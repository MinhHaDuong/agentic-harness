// erg — validate, ready, archive, graph %erg v1 files.
// No external dependencies (stdlib only).
//
// Usage:
//
//	erg validate [dir|file ...]
//	erg ready    [dir] [--json]
//	erg archive  [dir] [--days N] [--execute]
//	erg graph    [dir] [--json]
//	erg next-id  [dir]
package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

// ---------------------------------------------------------------------------
// Erg parser — %erg v1 format
// ---------------------------------------------------------------------------

const magicLine = "%erg v1"

type Erg struct {
	Path     string
	Headers  map[string][]string // repeatable headers
	LogLines []string
	Body     string
	HasMagic bool
	HasLog   bool
	HasBody  bool
}

func (t *Erg) Title() string {
	if vs, ok := t.Headers["Title"]; ok && len(vs) > 0 {
		return vs[0]
	}
	return ""
}

func (t *Erg) Status() string {
	if vs, ok := t.Headers["Status"]; ok && len(vs) > 0 {
		return vs[0]
	}
	return ""
}

func (t *Erg) BlockedBy() []string {
	if vs, ok := t.Headers["Blocked-by"]; ok {
		return vs
	}
	return nil
}

func (t *Erg) Filename() string {
	return filepath.Base(t.Path)
}

// FilenameID extracts the numeric prefix from the filename (e.g., "0042" from "0042-add-auth.erg").
func (t *Erg) FilenameID() string {
	stem := strings.TrimSuffix(t.Filename(), ".erg")
	if idx := strings.Index(stem, "-"); idx > 0 {
		return stem[:idx]
	}
	return stem
}

func isLetter(c byte) bool {
	return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z')
}

func isAlphanumeric(c byte) bool {
	return isLetter(c) || (c >= '0' && c <= '9')
}

// parseHeaderLine extracts "Key: value" from a line.
func parseHeaderLine(line string) (string, string, bool) {
	if len(line) == 0 || !isLetter(line[0]) {
		return "", "", false
	}
	colonPos := -1
	for i := 1; i < len(line); i++ {
		c := line[i]
		if c == ':' {
			colonPos = i
			break
		}
		if isAlphanumeric(c) || c == '_' || c == '-' {
			continue
		}
		if c == ' ' || c == '\t' {
			for j := i; j < len(line); j++ {
				if line[j] == ':' {
					colonPos = j
					break
				}
				if line[j] != ' ' && line[j] != '\t' {
					return "", "", false
				}
			}
			break
		}
		return "", "", false
	}
	if colonPos < 0 {
		return "", "", false
	}
	key := strings.TrimSpace(line[:colonPos])
	val := strings.TrimSpace(line[colonPos+1:])
	return key, val, true
}

func parseErg(path string) Erg {
	data, err := os.ReadFile(path)
	if err != nil {
		return Erg{Path: path, Headers: make(map[string][]string)}
	}
	lines := strings.Split(string(data), "\n")

	headers := make(map[string][]string)
	var logLines, bodyLines []string
	section := "magic" // magic | headers | gap | log | body
	hasMagic := false
	hasLog := false
	hasBody := false

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)

		// First non-empty line must be the magic line
		if section == "magic" {
			if trimmed == "" {
				continue
			}
			if trimmed == magicLine {
				hasMagic = true
				section = "headers"
				continue
			}
			// No magic line — try to parse as old format
			section = "headers"
			// Fall through to header parsing
		}

		if !hasBody && trimmed == "--- log ---" {
			section = "log"
			hasLog = true
			continue
		}
		if !hasBody && trimmed == "--- body ---" {
			section = "body"
			hasBody = true
			continue
		}

		switch section {
		case "headers":
			if trimmed == "" {
				section = "gap"
				continue
			}
			if key, val, ok := parseHeaderLine(line); ok {
				headers[key] = append(headers[key], val)
			}
		case "gap":
			// ignore lines between header block and log separator
		case "log":
			if trimmed != "" {
				logLines = append(logLines, line)
			}
		case "body":
			bodyLines = append(bodyLines, line)
		}
	}

	return Erg{
		Path:     path,
		Headers:  headers,
		LogLines: logLines,
		Body:     strings.Join(bodyLines, "\n"),
		HasMagic: hasMagic,
		HasLog:   hasLog,
		HasBody:  hasBody,
	}
}

func loadErgs(dir string) []Erg {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil
	}
	var tickets []Erg
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(e.Name(), ".erg") {
			tickets = append(tickets, parseErg(filepath.Join(dir, e.Name())))
		}
	}
	sort.Slice(tickets, func(i, j int) bool {
		return tickets[i].Filename() < tickets[j].Filename()
	})
	return tickets
}

// ---------------------------------------------------------------------------
// Validate — %erg v1 rules
// ---------------------------------------------------------------------------

var (
	requiredHeaders = []string{"Title", "Status", "Created", "Author"}
	validHeaders    = map[string]bool{
		"Title": true, "Status": true, "Created": true,
		"Author": true, "Blocked-by": true,
	}
	validStatuses = map[string]bool{
		"open": true, "doing": true, "closed": true, "pending": true,
	}
	isoDateRE = regexp.MustCompile(`^\d{4}-\d{2}-\d{2}$`)
	// Filename: 4-digit ID, dash, lowercase kebab slug
	filenameRE = regexp.MustCompile(`^\d{4}-[a-z0-9]+(-[a-z0-9]+)*\.erg$`)
	// Log line: ISO timestamp, space, actor, space, verb [detail]
	logLineRE = regexp.MustCompile(`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z\s+\S+\s+\S+`)

	validBumpCategories = map[string]bool{
		"permission":      true,
		"author-decision": true,
		"test-failure":    true,
		"verify-reroll":   true,
		"circuit-breaker": true,
	}
)

// validateLogLine checks a single log line for format and bump-category validity.
// Returns nil if valid, or a descriptive error if invalid.
// Indented continuation lines (RFC 822 style) are accepted as-is.
func validateLogLine(line string) error {
	// Accept indented continuation lines (RFC 822 folding convention).
	if len(line) > 0 && (line[0] == ' ' || line[0] == '\t') {
		return nil
	}
	trimmed := strings.TrimSpace(line)
	if trimmed == "" {
		return nil
	}
	if !logLineRE.MatchString(trimmed) {
		return fmt.Errorf("malformed log line: %q", trimmed)
	}
	fields := strings.Fields(trimmed)
	if len(fields) >= 3 && fields[2] == "bump" {
		if len(fields) < 4 {
			return fmt.Errorf("bump verb requires a category; valid: permission, author-decision, test-failure, verify-reroll, circuit-breaker")
		}
		if !validBumpCategories[fields[3]] {
			return fmt.Errorf("unknown bump category %q; valid: permission, author-decision, test-failure, verify-reroll, circuit-breaker", fields[3])
		}
	}
	return nil
}

func validateErg(t *Erg, allIDs map[string]bool) []string {
	var errors []string
	name := t.Filename()

	// Rule 1: magic first line
	if !t.HasMagic {
		errors = append(errors, fmt.Sprintf("%s: missing magic first line '%%erg v1'", name))
	}

	// Rule 2: required headers
	for _, hdr := range requiredHeaders {
		if _, ok := t.Headers[hdr]; !ok {
			errors = append(errors, fmt.Sprintf("%s: missing required header '%s'", name, hdr))
		}
	}

	// Rule 3: no unknown headers
	for key := range t.Headers {
		if !validHeaders[key] {
			errors = append(errors, fmt.Sprintf("%s: unknown header '%s' (not in v1 closed set)", name, key))
		}
	}

	// Rule 4: valid Status
	status := t.Status()
	if status != "" && !validStatuses[status] {
		keys := sortedKeys(validStatuses)
		errors = append(errors, fmt.Sprintf(
			"%s: invalid Status '%s' (expected one of: %s)", name, status, strings.Join(keys, ", ")))
	}

	// Rule 5: Created is ISO date
	if created, ok := t.Headers["Created"]; ok && len(created) > 0 {
		if created[0] != "" && !isoDateRE.MatchString(created[0]) {
			errors = append(errors, fmt.Sprintf(
				"%s: Created '%s' is not a valid ISO date (YYYY-MM-DD)", name, created[0]))
		}
	}

	// Rule 6: filename matches NNNN-slug.erg
	if !filenameRE.MatchString(name) {
		errors = append(errors, fmt.Sprintf(
			"%s: filename does not match NNNN-slug.erg pattern", name))
	}

	// Rule 8: Blocked-by refs exist
	for _, refID := range t.BlockedBy() {
		if strings.HasPrefix(refID, "gh#") {
			continue // GitHub issue reference — not validated locally
		}
		if !allIDs[refID] {
			errors = append(errors, fmt.Sprintf(
				"%s: Blocked-by '%s' references unknown ticket ID", name, refID))
		}
	}

	// Rule 10: log lines match format (and bump verb has valid category)
	for _, line := range t.LogLines {
		if err := validateLogLine(line); err != nil {
			errors = append(errors, fmt.Sprintf("%s: %s", name, err))
		}
	}

	// Rule 11: both separators present
	if !t.HasLog {
		errors = append(errors, fmt.Sprintf("%s: missing '--- log ---' separator", name))
	}
	if !t.HasBody {
		errors = append(errors, fmt.Sprintf("%s: missing '--- body ---' separator", name))
	}

	return errors
}

func detectCycles(tickets []Erg) []string {
	var errors []string

	adj := make(map[string][]string)
	for i := range tickets {
		id := tickets[i].FilenameID()
		if id != "" {
			var localRefs []string
			for _, ref := range tickets[i].BlockedBy() {
				if !strings.HasPrefix(ref, "gh#") {
					localRefs = append(localRefs, ref)
				}
			}
			adj[id] = localRefs
		}
	}

	const (
		white = 0
		gray  = 1
		black = 2
	)
	color := make(map[string]int)
	for id := range adj {
		color[id] = white
	}

	// Use a shared stack with explicit push/pop to avoid Go slice aliasing bugs.
	var stack []string

	var dfs func(node string)
	dfs = func(node string) {
		color[node] = gray
		stack = append(stack, node) // push
		for _, neighbor := range adj[node] {
			c, exists := color[neighbor]
			if !exists {
				continue
			}
			if c == gray {
				start := 0
				for i, n := range stack {
					if n == neighbor {
						start = i
						break
					}
				}
				cycle := append([]string{}, stack[start:]...)
				cycle = append(cycle, neighbor)
				errors = append(errors, "dependency cycle: "+strings.Join(cycle, " -> "))
			} else if c == white {
				dfs(neighbor)
			}
		}
		stack = stack[:len(stack)-1] // pop
		color[node] = black
	}

	ids := sortedKeys2(adj)
	for _, id := range ids {
		if color[id] == white {
			dfs(id)
		}
	}
	return errors
}

// validateAll validates a set of tickets.
// subset: the tickets to run per-ticket rules on (the explicitly requested files).
// fullContext: the full directory contents used for Rule 7 (duplicates), Rule 8
// (ref existence), and Rule 9 (cycle detection). When called with a directory
// arg, subset == fullContext. When called with file args, fullContext is the
// parent dir load and subset is only the passed files.
// extraIDs: archived ticket IDs (valid Blocked-by targets, collision source).
func validateAll(subset []Erg, fullContext []Erg, extraIDs map[string]bool) []string {
	var errors []string

	// Rule 7: no duplicate IDs — run over fullContext
	idToFiles := make(map[string][]string)
	for i := range fullContext {
		id := fullContext[i].FilenameID()
		if id != "" {
			idToFiles[id] = append(idToFiles[id], fullContext[i].Filename())
		}
	}

	dupIDs := sortedKeys2(idToFiles)
	for _, tid := range dupIDs {
		files := idToFiles[tid]
		if len(files) > 1 {
			errors = append(errors, fmt.Sprintf(
				"duplicate ID '%s' in: %s", tid, strings.Join(files, ", ")))
		}
	}

	// Check collisions with archived ticket IDs (using fullContext IDs)
	if extraIDs != nil {
		for tid := range idToFiles {
			if extraIDs[tid] {
				errors = append(errors, fmt.Sprintf(
					"ID '%s' in %s collides with an archived ticket",
					tid, strings.Join(idToFiles[tid], ", ")))
			}
		}
	}

	// Build allIDs for reference checking — from fullContext + extraIDs
	allIDs := make(map[string]bool)
	for id := range idToFiles {
		allIDs[id] = true
	}
	for id := range extraIDs {
		allIDs[id] = true
	}

	// Per-ticket validation — iterate subset only
	for i := range subset {
		errors = append(errors, validateErg(&subset[i], allIDs)...)
	}

	// Rule 9: dependency cycles — run over fullContext
	errors = append(errors, detectCycles(fullContext)...)
	return errors
}

func cmdValidate(args []string) int {
	if len(args) == 0 {
		args = []string{"tickets/"}
	}

	// Pass 1: collect context dirs and subset (explicitly passed) files.
	// For a directory arg: it is both a context dir and its tickets are the subset.
	// For a file arg: the file is the subset, its parent dir is the context dir.
	contextDirs := make(map[string]bool) // cleaned dir paths, deduped
	var subsetTickets []Erg

	for _, arg := range args {
		info, err := os.Stat(arg)
		if err != nil {
			fmt.Printf("WARNING: skipping %s (%v)\n", arg, err)
			continue
		}
		if info.IsDir() {
			dir := filepath.Clean(arg)
			contextDirs[dir] = true
			subsetTickets = append(subsetTickets, loadErgs(arg)...)
		} else if strings.HasSuffix(arg, ".erg") {
			dir := filepath.Clean(filepath.Dir(arg))
			contextDirs[dir] = true
			subsetTickets = append(subsetTickets, parseErg(arg))
		} else {
			fmt.Printf("WARNING: skipping %s (not a .erg file or directory)\n", arg)
		}
	}

	if len(subsetTickets) == 0 {
		fmt.Println("No .erg files found.")
		return 0
	}

	// Pass 2: load full context from each context dir.
	// Build a set of subset paths to avoid double-counting per-ticket rules,
	// but fullContext includes everything for Rule 7/8/9.
	subsetPaths := make(map[string]bool)
	for i := range subsetTickets {
		subsetPaths[filepath.Clean(subsetTickets[i].Path)] = true
	}

	var contextTickets []Erg
	seenContextPaths := make(map[string]bool)
	for dir := range contextDirs {
		for _, t := range loadErgs(dir) {
			cleanPath := filepath.Clean(t.Path)
			if seenContextPaths[cleanPath] {
				continue
			}
			seenContextPaths[cleanPath] = true
			contextTickets = append(contextTickets, t)
		}
	}
	sort.Slice(contextTickets, func(i, j int) bool {
		return contextTickets[i].Filename() < contextTickets[j].Filename()
	})

	// Load archived ticket IDs as valid Blocked-by targets.
	// Fire for every context dir (covers both dir args and parent dirs of file args).
	extraIDs := make(map[string]bool)
	for dir := range contextDirs {
		archiveDir := filepath.Join(dir, "archive")
		if info, err := os.Stat(archiveDir); err == nil && info.IsDir() {
			for _, at := range loadErgs(archiveDir) {
				id := at.FilenameID()
				if id != "" {
					extraIDs[id] = true
				}
			}
		}
	}

	errors := validateAll(subsetTickets, contextTickets, extraIDs)
	if len(errors) > 0 {
		fmt.Printf("ERG VALIDATION FAILED (%d error(s)):\n", len(errors))
		for _, e := range errors {
			fmt.Printf("  %s\n", e)
		}
		return 1
	}

	fmt.Printf("ERG VALIDATION: PASS (%d tickets)\n", len(subsetTickets))
	return 0
}

// ---------------------------------------------------------------------------
// Ready — find unblocked open tickets
// ---------------------------------------------------------------------------

type readyEntry struct {
	id, title, file string
	cache           string // "hit", "miss", "skip"
	hash            string // current body hash (12 hex)
	scope           string // cached scope (cache:hit only)
	risk            string // cached risk (cache:hit only)
	skipReason      string // cached reason (cache:skip only)
}

// bodyHash returns the SHA-256 of the body content before the first
// "## Picker assessment" section, hex-encoded, first 12 chars.
func bodyHash(body string) string {
	core := body
	if idx := strings.Index(body, "\n## Picker assessment"); idx >= 0 {
		core = body[:idx+1]
	} else if strings.HasPrefix(body, "## Picker assessment") {
		core = ""
	}
	// Normalise trailing newlines so the hash is stable regardless of how many
	// blank lines precede the assessment section or end the body.
	core = strings.TrimRight(core, "\n")
	sum := sha256.Sum256([]byte(core))
	return hex.EncodeToString(sum[:])[:12]
}

type sweepCacheInfo struct {
	cacheType  string // "hit", "miss", "skip"
	hash       string // 12-hex hash from log line
	scope      string // e.g. "30m/4f"
	risk       string // e.g. "low"
	skipReason string // for skip
}

// parseSweepCache scans log lines (last-wins) for sweep-skip / sweep-assess /
// sweep-pick lines and extracts their key:value tokens.
func parseSweepCache(logLines []string) sweepCacheInfo {
	for i := len(logLines) - 1; i >= 0; i-- {
		line := logLines[i]
		isSkip := strings.Contains(line, " note sweep-skip:")
		isAssess := strings.Contains(line, " note sweep-assess:") ||
			strings.Contains(line, " note sweep-pick:")
		if !isSkip && !isAssess {
			continue
		}
		info := sweepCacheInfo{}
		if isSkip {
			info.cacheType = "skip"
		} else {
			info.cacheType = "hit"
		}
		extractToken := func(key string) string {
			prefix := key + ":"
			idx := strings.Index(line, prefix)
			if idx < 0 {
				return ""
			}
			rest := line[idx+len(prefix):]
			if sp := strings.IndexByte(rest, ' '); sp >= 0 {
				return rest[:sp]
			}
			return rest
		}
		info.hash = extractToken("hash")
		info.scope = extractToken("scope")
		info.risk = extractToken("risk")
		info.skipReason = extractToken("reason")
		// For sweep-skip with an expires: token, demote to miss if expiry passed.
		if isSkip {
			if exp := extractToken("expires"); exp != "" {
				exp = strings.TrimRight(exp, "Z") // tolerate trailing Z
				layouts := []string{"2006-01-02T15:04:05", "2006-01-02T15:04", "2006-01-02"}
				var expTime time.Time
				for _, lay := range layouts {
					if t, err := time.Parse(lay, exp); err == nil {
						expTime = t
						break
					}
				}
				if !expTime.IsZero() && time.Now().UTC().After(expTime) {
					info.cacheType = "miss" // expired — force reassessment
				}
			}
		}
		return info
	}
	return sweepCacheInfo{cacheType: "miss"}
}

// appendToTicket appends logLine before "--- body ---" and bodySection at end
// of body, writing the result in place.
func appendToTicket(path, logLine, bodySection string) error {
	raw, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	sep := []byte("--- body ---\n")
	idx := bytes.Index(raw, sep)
	if idx < 0 {
		return fmt.Errorf("%s: no --- body --- separator", path)
	}
	beforeBody := raw[:idx]
	bodyContent := raw[idx+len(sep):]

	if !bytes.HasSuffix(beforeBody, []byte("\n")) {
		beforeBody = append(beforeBody, '\n')
	}
	logAppend := []byte(logLine + "\n")

	if !bytes.HasSuffix(bodyContent, []byte("\n")) {
		bodyContent = append(bodyContent, '\n')
	}
	bodyAppend := []byte(bodySection)

	result := make([]byte, 0, len(beforeBody)+len(logAppend)+len(sep)+len(bodyContent)+len(bodyAppend))
	result = append(result, beforeBody...)
	result = append(result, logAppend...)
	result = append(result, sep...)
	result = append(result, bodyContent...)
	result = append(result, bodyAppend...)
	return os.WriteFile(path, result, 0644)
}

func loadWip() map[string]string {
	wip := make(map[string]string)
	cmd := exec.Command("git", "rev-parse", "--git-common-dir")
	out, err := cmd.Output()
	if err != nil {
		return wip
	}
	wipDir := filepath.Join(strings.TrimSpace(string(out)), "ticket-wip")
	entries, err := os.ReadDir(wipDir)
	if err != nil {
		return wip
	}
	for _, e := range entries {
		if e.IsDir() || filepath.Ext(e.Name()) != ".wip" {
			continue
		}
		tid := strings.TrimSuffix(e.Name(), ".wip")
		data, err := os.ReadFile(filepath.Join(wipDir, e.Name()))
		if err == nil {
			wip[tid] = strings.TrimSpace(string(data))
		}
	}
	return wip
}

func cmdReady(args []string) int {
	useJSON := false
	var rest []string
	for _, a := range args {
		if a == "--json" {
			useJSON = true
		} else {
			rest = append(rest, a)
		}
	}

	ticketDir := "tickets"
	if len(rest) > 0 {
		ticketDir = rest[0]
	}

	info, err := os.Stat(ticketDir)
	if err != nil || !info.IsDir() {
		fmt.Printf("Directory not found: %s\n", ticketDir)
		return 1
	}

	tickets := loadErgs(ticketDir)
	statusByID := make(map[string]string)
	for i := range tickets {
		id := tickets[i].FilenameID()
		if id != "" {
			statusByID[id] = tickets[i].Status()
		}
	}

	wip := loadWip()

	var warnings []string
	var ready []readyEntry
	openCount := 0

	for i := range tickets {
		t := &tickets[i]
		if t.Status() != "open" {
			continue
		}
		openCount++

		// Exclude WIP-claimed tickets
		tid := t.FilenameID()
		if _, claimed := wip[tid]; claimed {
			continue
		}

		blocked := false
		for _, refID := range t.BlockedBy() {
			if strings.HasPrefix(refID, "gh#") {
				continue // GitHub refs treated as satisfied offline
			}
			refStatus, found := statusByID[refID]
			if !found {
				warnings = append(warnings, fmt.Sprintf(
					"%s: Blocked-by '%s' not found (treating as satisfied)", t.Filename(), refID))
			} else if refStatus != "closed" {
				blocked = true
				break
			}
		}
		if !blocked {
			h := bodyHash(t.Body)
			cached := parseSweepCache(t.LogLines)
			cacheType := "miss"
			scope, risk, skipReason := "", "", ""
			if cached.hash == h {
				cacheType = cached.cacheType
				scope = cached.scope
				risk = cached.risk
				skipReason = cached.skipReason
			}
			ready = append(ready, readyEntry{tid, t.Title(), t.Filename(),
				cacheType, h, scope, risk, skipReason})
		}
	}

	for _, w := range warnings {
		fmt.Fprintf(os.Stderr, "WARNING: %s\n", w)
	}

	if useJSON {
		if len(ready) == 0 {
			fmt.Println("[]")
		} else {
			fmt.Println("[")
			for i, r := range ready {
				comma := ","
				if i == len(ready)-1 {
					comma = ""
				}
				extra := fmt.Sprintf(",\n    \"cache\": \"%s\",\n    \"hash\": \"%s\"",
					jsonEscape(r.cache), jsonEscape(r.hash))
				switch r.cache {
				case "hit":
					extra += fmt.Sprintf(",\n    \"scope\": \"%s\",\n    \"risk\": \"%s\"",
						jsonEscape(r.scope), jsonEscape(r.risk))
				case "skip":
					extra += fmt.Sprintf(",\n    \"skip_reason\": \"%s\"", jsonEscape(r.skipReason))
				}
				if w, ok := wip[r.id]; ok {
					extra += fmt.Sprintf(",\n    \"wip\": \"%s\"", jsonEscape(w))
				}
				fmt.Printf("  {\n    \"id\": \"%s\",\n    \"title\": \"%s\",\n    \"file\": \"%s\"%s\n  }%s\n",
					jsonEscape(r.id), jsonEscape(r.title), jsonEscape(r.file), extra, comma)
			}
			fmt.Println("]")
		}
	} else {
		if len(ready) == 0 {
			if len(tickets) == 0 {
				fmt.Println("No tickets found.")
			} else if openCount == 0 {
				fmt.Printf("All %d tickets are closed.\n", len(tickets))
			} else {
				fmt.Printf("%d open tickets, all blocked.\n", openCount)
			}
		} else {
			fmt.Printf("Ready tickets (%d):\n", len(ready))
			for _, r := range ready {
				suffix := ""
				if w, ok := wip[r.id]; ok {
					suffix = "  (wip: " + w + ")"
				}
				fmt.Printf("  %-8s %-40s %s%s\n", r.id, r.file, r.title, suffix)
			}
		}
	}
	return 0
}

func jsonEscape(s string) string {
	s = strings.ReplaceAll(s, `\`, `\\`)
	s = strings.ReplaceAll(s, `"`, `\"`)
	s = strings.ReplaceAll(s, "\n", `\n`)
	s = strings.ReplaceAll(s, "\r", `\r`)
	s = strings.ReplaceAll(s, "\t", `\t`)
	return s
}

// ---------------------------------------------------------------------------
// Archive — DAG-safe archival of old closed tickets
// ---------------------------------------------------------------------------

// parseLogTimestamp extracts a time from a log line's ISO-8601 prefix.
func parseLogTimestamp(line string) (time.Time, bool) {
	line = strings.TrimSpace(line)
	if len(line) < 16 {
		return time.Time{}, false
	}
	tsStr := line
	if idx := strings.IndexByte(line[16:], ' '); idx >= 0 {
		tsStr = line[:16+idx]
	}
	tsStr = strings.TrimRight(tsStr, "Z")

	if t, err := time.Parse("2006-01-02T15:04:05", tsStr); err == nil {
		return t, true
	}
	if t, err := time.Parse("2006-01-02T15:04", tsStr); err == nil {
		return t, true
	}
	return time.Time{}, false
}

func cmdArchive(args []string) int {
	execute := false
	days := 90
	ticketDir := "tickets"

	var filtered []string
	for _, a := range args {
		if a == "--execute" {
			execute = true
		} else {
			filtered = append(filtered, a)
		}
	}

	for i := 0; i < len(filtered); i++ {
		a := filtered[i]
		if strings.HasPrefix(a, "--days=") {
			if n, err := strconv.Atoi(a[7:]); err == nil {
				days = n
			}
		} else if a == "--days" && i+1 < len(filtered) {
			if n, err := strconv.Atoi(filtered[i+1]); err == nil {
				days = n
			}
			i++
		} else if !strings.HasPrefix(a, "--") {
			ticketDir = a
		}
	}

	info, err := os.Stat(ticketDir)
	if err != nil || !info.IsDir() {
		fmt.Printf("Directory not found: %s\n", ticketDir)
		return 1
	}

	tickets := loadErgs(ticketDir)
	cutoff := time.Now().UTC().AddDate(0, 0, -days)

	// Collect all IDs referenced by Blocked-by in live tickets
	referencedIDs := make(map[string]bool)
	allErgs := append([]Erg{}, tickets...)
	archiveDir := filepath.Join(ticketDir, "archive")
	if info, err := os.Stat(archiveDir); err == nil && info.IsDir() {
		allErgs = append(allErgs, loadErgs(archiveDir)...)
	}
	for i := range allErgs {
		for _, ref := range allErgs[i].BlockedBy() {
			if !strings.HasPrefix(ref, "gh#") {
				referencedIDs[ref] = true
			}
		}
	}

	var archivable, dagProtected []Erg
	for i := range tickets {
		t := &tickets[i]
		if t.Status() != "closed" {
			continue
		}

		// Determine age from last log line or Created header
		var lastTime time.Time
		var hasTime bool
		if len(t.LogLines) > 0 {
			lastTime, hasTime = parseLogTimestamp(t.LogLines[len(t.LogLines)-1])
		}
		if !hasTime {
			if created, ok := t.Headers["Created"]; ok && len(created) > 0 {
				if ct, err := time.Parse("2006-01-02", created[0]); err == nil {
					lastTime = ct
					hasTime = true
				}
			}
		}
		if !hasTime || !lastTime.Before(cutoff) {
			continue
		}

		id := t.FilenameID()
		if referencedIDs[id] {
			dagProtected = append(dagProtected, *t)
		} else {
			archivable = append(archivable, *t)
		}
	}

	if len(dagProtected) > 0 {
		var ids []string
		for _, t := range dagProtected {
			ids = append(ids, t.FilenameID())
		}
		fmt.Printf("DAG-protected (skipping %d): %s\n", len(dagProtected), strings.Join(ids, ", "))
	}

	if len(archivable) == 0 {
		fmt.Printf("Nothing to archive (threshold: %d days).\n", days)
		return 0
	}

	var ids []string
	for _, t := range archivable {
		ids = append(ids, t.FilenameID())
	}
	fmt.Printf("Will archive %d ticket(s): %s\n", len(archivable), strings.Join(ids, ", "))

	if !execute {
		fmt.Println("Dry run. Pass --execute to proceed.")
		return 0
	}

	os.MkdirAll(archiveDir, 0755)

	for _, t := range archivable {
		dest := filepath.Join(archiveDir, t.Filename())
		cmd := exec.Command("git", "mv", t.Path, dest)
		if err := cmd.Run(); err != nil {
			fmt.Fprintf(os.Stderr, "git mv failed for %s\n", t.Filename())
			return 1
		}
		fmt.Printf("  moved %s\n", t.Filename())
	}

	msg := fmt.Sprintf("archive %d closed tickets (>%d days, DAG-safe)", len(archivable), days)
	cmd := exec.Command("git", "commit", "-m", msg)
	if err := cmd.Run(); err != nil {
		fmt.Fprintln(os.Stderr, "git commit failed")
		return 1
	}
	fmt.Printf("Committed: %s\n", msg)
	return 0
}

// ---------------------------------------------------------------------------
// Graph — visualize the ticket dependency DAG
// ---------------------------------------------------------------------------

func cmdGraph(args []string) int {
	useJSON := false
	var rest []string
	for _, a := range args {
		if a == "--json" {
			useJSON = true
		} else {
			rest = append(rest, a)
		}
	}

	ticketDir := "tickets"
	if len(rest) > 0 {
		ticketDir = rest[0]
	}

	info, err := os.Stat(ticketDir)
	if err != nil || !info.IsDir() {
		fmt.Printf("Directory not found: %s\n", ticketDir)
		return 1
	}

	tickets := loadErgs(ticketDir)
	if len(tickets) == 0 {
		fmt.Println("No tickets found.")
		return 0
	}

	// Build lookup maps
	byID := make(map[string]*Erg)
	statusByID := make(map[string]string)
	for i := range tickets {
		id := tickets[i].FilenameID()
		if id != "" {
			byID[id] = &tickets[i]
			statusByID[id] = tickets[i].Status()
		}
	}

	wip := loadWip()

	// Build children map (reverse of Blocked-by): if B is blocked by A, then A -> B
	children := make(map[string][]string)
	hasParent := make(map[string]bool)
	for i := range tickets {
		id := tickets[i].FilenameID()
		for _, ref := range tickets[i].BlockedBy() {
			if strings.HasPrefix(ref, "gh#") {
				continue
			}
			if _, exists := byID[ref]; exists {
				children[ref] = append(children[ref], id)
				hasParent[id] = true
			}
		}
	}

	// Sort children for deterministic output
	for k := range children {
		sort.Strings(children[k])
	}

	// Determine annotation for a ticket
	annotate := func(id string) string {
		status := statusByID[id]
		if _, claimed := wip[id]; claimed {
			return status + ", claimed"
		}
		if status == "open" {
			// Check if blocked
			t := byID[id]
			for _, ref := range t.BlockedBy() {
				if strings.HasPrefix(ref, "gh#") {
					continue
				}
				if s, ok := statusByID[ref]; ok && s != "closed" {
					return "open, blocked"
				}
			}
			return "open, READY"
		}
		return status
	}

	// Find root nodes (no parent in the DAG)
	var roots []string
	for i := range tickets {
		id := tickets[i].FilenameID()
		if id != "" && !hasParent[id] {
			roots = append(roots, id)
		}
	}
	sort.Strings(roots)

	if useJSON {
		type jsonNode struct {
			id, title, status, annotation string
			blockedBy                     []string
			deps                          []string
		}
		var nodes []jsonNode
		for i := range tickets {
			id := tickets[i].FilenameID()
			n := jsonNode{
				id:         id,
				title:      tickets[i].Title(),
				status:     tickets[i].Status(),
				annotation: annotate(id),
				blockedBy:  tickets[i].BlockedBy(),
				deps:       children[id],
			}
			nodes = append(nodes, n)
		}
		fmt.Println("[")
		for i, n := range nodes {
			comma := ","
			if i == len(nodes)-1 {
				comma = ""
			}
			blockedByJSON := "[]"
			if len(n.blockedBy) > 0 {
				var parts []string
				for _, b := range n.blockedBy {
					parts = append(parts, fmt.Sprintf("\"%s\"", jsonEscape(b)))
				}
				blockedByJSON = "[" + strings.Join(parts, ", ") + "]"
			}
			depsJSON := "[]"
			if len(n.deps) > 0 {
				var parts []string
				for _, d := range n.deps {
					parts = append(parts, fmt.Sprintf("\"%s\"", jsonEscape(d)))
				}
				depsJSON = "[" + strings.Join(parts, ", ") + "]"
			}
			fmt.Printf("  {\n    \"id\": \"%s\",\n    \"title\": \"%s\",\n    \"status\": \"%s\",\n    \"annotation\": \"%s\",\n    \"blocked_by\": %s,\n    \"unblocks\": %s\n  }%s\n",
				jsonEscape(n.id), jsonEscape(n.title), jsonEscape(n.status), jsonEscape(n.annotation), blockedByJSON, depsJSON, comma)
		}
		fmt.Println("]")
		return 0
	}

	// ASCII tree output
	var printTree func(id string, prefix string, isLast bool)
	printTree = func(id string, prefix string, isLast bool) {
		t := byID[id]
		if t == nil {
			return
		}
		ann := annotate(id)
		connector := "-> "
		if prefix == "" {
			connector = ""
		}
		fmt.Printf("%s%s%s %s [%s]\n", prefix, connector, id, t.Title(), ann)

		kids := children[id]
		childPrefix := prefix
		if prefix != "" {
			if isLast {
				childPrefix = prefix[:len(prefix)-3] + "   "
			} else {
				childPrefix = prefix[:len(prefix)-3] + "|  "
			}
		}
		for i, kid := range kids {
			last := i == len(kids)-1
			if childPrefix == "" {
				printTree(kid, "   ", last)
			} else {
				printTree(kid, childPrefix+"   ", last)
			}
		}
	}

	for _, root := range roots {
		printTree(root, "", true)
	}

	return 0
}

// ---------------------------------------------------------------------------
// Next-ID — print the next available ticket ID
// ---------------------------------------------------------------------------

func cmdNextID(args []string) int {
	ticketDir := "tickets"
	if len(args) > 0 {
		ticketDir = args[0]
	}

	maxID := 0

	// Scan both tickets/ and tickets/archive/
	for _, dir := range []string{ticketDir, filepath.Join(ticketDir, "archive")} {
		entries, err := os.ReadDir(dir)
		if err != nil {
			continue
		}
		for _, e := range entries {
			if e.IsDir() || !strings.HasSuffix(e.Name(), ".erg") {
				continue
			}
			stem := strings.TrimSuffix(e.Name(), ".erg")
			if idx := strings.Index(stem, "-"); idx > 0 {
				stem = stem[:idx]
			}
			if n, err := strconv.Atoi(stem); err == nil && n > maxID {
				maxID = n
			}
		}
	}

	fmt.Printf("%04d\n", maxID+1)
	return 0
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func sortedKeys(m map[string]bool) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

func sortedKeys2[V any](m map[string]V) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// ---------------------------------------------------------------------------
// sweep-write — write picker assessment only when body changed
// ---------------------------------------------------------------------------

// cmdSweepSkip writes a sweep-skip log line to a ticket file only when the
// current body hash differs from the cached sweep-skip hash.
// Usage: erg sweep-skip <ticket.erg> <reason> [expires:<ISO8601>]
// Outputs "WROTE" or "CACHED" to stdout.
func cmdSweepSkip(args []string) int {
	if len(args) < 2 {
		fmt.Fprintln(os.Stderr, "Usage: erg sweep-skip <ticket.erg> <reason> [expires:<ISO8601>]")
		return 1
	}
	path := args[0]
	reason := args[1]
	expires := ""
	for _, a := range args[2:] {
		if strings.HasPrefix(a, "expires:") {
			expires = a[8:]
		}
	}

	t := parseErg(path)
	if !t.HasBody {
		fmt.Fprintf(os.Stderr, "error: %s has no --- body --- section\n", path)
		return 1
	}

	hash := bodyHash(t.Body)
	cached := parseSweepCache(t.LogLines)
	if cached.cacheType == "skip" && cached.hash == hash {
		fmt.Println("CACHED")
		return 0
	}

	ts := time.Now().UTC().Format("2006-01-02T15:04Z")
	logLine := fmt.Sprintf("%s claude note sweep-skip: %s hash:%s", ts, reason, hash)
	if expires != "" {
		logLine += " expires:" + expires
	}

	raw, err := os.ReadFile(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}
	sep := []byte("--- body ---\n")
	idx := bytes.Index(raw, sep)
	if idx < 0 {
		fmt.Fprintf(os.Stderr, "error: %s has no --- body --- separator\n", path)
		return 1
	}
	// Build result in a fresh buffer. Do NOT take a sub-slice of raw and
	// append into it: os.ReadFile returns a slice with cap > len, so
	// `raw[:idx]` shares the backing array and a subsequent append
	// silently overwrites the body — corrupting it on disk.
	logAppend := []byte(logLine + "\n")
	bodyContent := raw[idx+len(sep):]
	result := make([]byte, 0, idx+1+len(logAppend)+len(sep)+len(bodyContent))
	result = append(result, raw[:idx]...)
	if !bytes.HasSuffix(result, []byte("\n")) {
		result = append(result, '\n')
	}
	result = append(result, logAppend...)
	result = append(result, sep...)
	result = append(result, bodyContent...)
	if err := os.WriteFile(path, result, 0644); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}
	fmt.Println("WROTE")
	return 0
}

// cmdSweepWrite writes a picker assessment (body section + log line) to a
// ticket file only when the current body hash differs from the cached one.
// Usage: erg sweep-write <ticket.erg> <picked|not-picked> <scope> <risk> <reason...>
// Outputs "WROTE" or "CACHED" to stdout.
func cmdSweepWrite(args []string) int {
	if len(args) < 5 {
		fmt.Fprintln(os.Stderr, "Usage: erg sweep-write <ticket.erg> <picked|not-picked> <scope> <risk> <reason...>")
		return 1
	}
	path := args[0]
	decision := args[1]
	scope := args[2]
	risk := args[3]
	reason := strings.Join(args[4:], " ")

	t := parseErg(path)
	if !t.HasBody {
		fmt.Fprintf(os.Stderr, "error: %s has no --- body --- section\n", path)
		return 1
	}

	hash := bodyHash(t.Body)
	cached := parseSweepCache(t.LogLines)
	if cached.hash == hash {
		fmt.Println("CACHED")
		return 0
	}

	verb := "sweep-assess"
	if decision == "picked" {
		verb = "sweep-pick"
	}
	ts := time.Now().UTC().Format("2006-01-02T15:04Z")
	logLine := fmt.Sprintf("%s claude note %s: %s hash:%s scope:%s risk:%s",
		ts, verb, decision, hash, scope, risk)
	assessSection := fmt.Sprintf("## Picker assessment %s\n**Decision:** %s\n**Scope:** %s\n**Risk:** %s\n**Reason:** %s\n",
		ts, decision, scope, risk, reason)

	if err := appendToTicket(path, logLine, assessSection); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}
	fmt.Println("WROTE")
	return 0
}

// ---------------------------------------------------------------------------
// Main dispatch
// ---------------------------------------------------------------------------

func printUsage() {
	fmt.Fprintln(os.Stderr, "Usage: erg <command> [args...]")
	fmt.Fprintln(os.Stderr)
	fmt.Fprintln(os.Stderr, "Commands:")
	fmt.Fprintf(os.Stderr, "  validate [dir|files...]   Validate %%erg v1 files\n")
	fmt.Fprintln(os.Stderr, "  ready [dir] [--json]      Show tickets ready for work")
	fmt.Fprintln(os.Stderr, "  archive [dir] [--days N] [--execute]  Archive old closed tickets")
	fmt.Fprintln(os.Stderr, "  graph [dir] [--json]      Show ticket dependency DAG")
	fmt.Fprintln(os.Stderr, "  next-id [dir]             Print the next available ticket ID")
	fmt.Fprintln(os.Stderr, "  sweep-skip <file> <reason> [expires:<ISO8601>]")
	fmt.Fprintln(os.Stderr, "                            Write sweep-skip log line if body changed")
	fmt.Fprintln(os.Stderr, "  sweep-write <file> <picked|not-picked> <scope> <risk> <reason>")
	fmt.Fprintln(os.Stderr, "                            Write picker assessment if body changed")
}

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	cmd := os.Args[1]
	rest := os.Args[2:]

	var exitCode int
	switch cmd {
	case "validate":
		exitCode = cmdValidate(rest)
	case "ready":
		exitCode = cmdReady(rest)
	case "archive":
		exitCode = cmdArchive(rest)
	case "graph":
		exitCode = cmdGraph(rest)
	case "next-id":
		exitCode = cmdNextID(rest)
	case "sweep-skip":
		exitCode = cmdSweepSkip(rest)
	case "sweep-write":
		exitCode = cmdSweepWrite(rest)
	case "-h", "--help", "help":
		printUsage()
		exitCode = 0
	default:
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n", cmd)
		printUsage()
		exitCode = 1
	}
	os.Exit(exitCode)
}
