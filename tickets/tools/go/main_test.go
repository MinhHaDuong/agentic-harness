package main

import (
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestBumpVerbValidation(t *testing.T) {
	cases := []struct {
		name    string
		line    string
		wantErr bool
	}{
		{
			name:    "valid bump permission",
			line:    "2026-04-23T09:00Z claude bump permission — awaiting gh pr create",
			wantErr: false,
		},
		{
			name:    "valid bump circuit-breaker",
			line:    "2026-04-23T09:00Z claude bump circuit-breaker — agent timeout",
			wantErr: false,
		},
		{
			name:    "valid bump author-decision",
			line:    "2026-04-23T09:00Z claude bump author-decision — non-autonomous call",
			wantErr: false,
		},
		{
			name:    "valid bump test-failure",
			line:    "2026-04-23T09:00Z claude bump test-failure — make check failed",
			wantErr: false,
		},
		{
			name:    "valid bump verify-reroll",
			line:    "2026-04-23T09:00Z claude bump verify-reroll — round 1: missing tests",
			wantErr: false,
		},
		{
			name:    "invalid bump category",
			line:    "2026-04-23T09:00Z claude bump unknown-category — foo",
			wantErr: true,
		},
		{
			name:    "bump with no category (too few fields)",
			line:    "2026-04-23T09:00Z claude bump",
			wantErr: true,
		},
		{
			name:    "existing verb unaffected",
			line:    "2026-04-23T09:00Z claude created",
			wantErr: false,
		},
		{
			name:    "note verb unaffected",
			line:    "2026-04-23T09:00Z claude note anything goes here",
			wantErr: false,
		},
		{
			name:    "indented continuation line accepted",
			line:    "  Handoff from cadens run — continuation of previous entry",
			wantErr: false,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			err := validateLogLine(tc.line)
			if tc.wantErr && err == nil {
				t.Errorf("expected error for line: %q", tc.line)
			}
			if !tc.wantErr && err != nil {
				t.Errorf("unexpected error for line %q: %v", tc.line, err)
			}
			if tc.wantErr && err != nil {
				// Error message should name the valid category set
				for _, cat := range []string{"permission", "author-decision", "test-failure", "verify-reroll", "circuit-breaker"} {
					if !strings.Contains(err.Error(), cat) {
						t.Errorf("error message missing category %q: %v", cat, err)
					}
				}
			}
		})
	}
}

// captureValidate runs cmdValidate(args) and returns exit code + captured stdout.
func captureValidate(args []string) (int, string) {
	old := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w
	exit := cmdValidate(args)
	w.Close()
	os.Stdout = old
	out, _ := io.ReadAll(r)
	return exit, string(out)
}

// minimalErg returns a valid %erg v1 ticket body with the given ID slug and
// optional Blocked-by header lines (each entry is a raw "Blocked-by: NNNN" line).
func minimalErg(id, slug string, blockedBy []string) string {
	var sb strings.Builder
	sb.WriteString("%erg v1\n")
	sb.WriteString("Title: test ticket " + id + "\n")
	sb.WriteString("Status: open\n")
	sb.WriteString("Created: 2026-04-26\n")
	sb.WriteString("Author: test\n")
	for _, dep := range blockedBy {
		sb.WriteString("Blocked-by: " + dep + "\n")
	}
	sb.WriteString("\n--- log ---\n")
	sb.WriteString("2026-04-26T00:00Z test created\n")
	sb.WriteString("\n--- body ---\n")
	sb.WriteString("Test body.\n")
	return sb.String()
}

// ---------------------------------------------------------------------------
// bodyHash
// ---------------------------------------------------------------------------

func TestBodyHashStableAcrossAssessments(t *testing.T) {
	body := "## Context\nSome work.\n\n## Actions\n1. Do it.\n"
	h1 := bodyHash(body)
	if len(h1) != 12 {
		t.Fatalf("expected 12 hex chars, got %d: %q", len(h1), h1)
	}
	// Appending a Picker assessment must not change the hash.
	bodyWithAssess := body + "\n## Picker assessment 2026-04-27T10:00Z\n**Decision:** not picked\n"
	h2 := bodyHash(bodyWithAssess)
	if h1 != h2 {
		t.Errorf("hash changed after appending assessment: %s → %s", h1, h2)
	}
	// Multiple assessments: still stable.
	bodyWith2 := bodyWithAssess + "\n## Picker assessment 2026-04-28T10:00Z\n**Decision:** picked\n"
	h3 := bodyHash(bodyWith2)
	if h1 != h3 {
		t.Errorf("hash changed after second assessment: %s → %s", h1, h3)
	}
}

func TestBodyHashChangesOnCoreEdit(t *testing.T) {
	body1 := "## Actions\n1. Original.\n"
	body2 := "## Actions\n1. Changed.\n"
	if bodyHash(body1) == bodyHash(body2) {
		t.Error("hash should differ for different body content")
	}
}

// ---------------------------------------------------------------------------
// parseSweepCache
// ---------------------------------------------------------------------------

func TestParseSweepCacheMiss(t *testing.T) {
	lines := []string{"2026-04-26T00:00Z claude created"}
	info := parseSweepCache(lines)
	if info.cacheType != "miss" {
		t.Errorf("expected miss, got %s", info.cacheType)
	}
}

func TestParseSweepCacheHit(t *testing.T) {
	hash := bodyHash("Some body.\n")
	lines := []string{
		"2026-04-26T00:00Z claude created",
		"2026-04-27T10:00Z claude note sweep-assess: not-picked hash:" + hash + " scope:30m/4f risk:low",
	}
	info := parseSweepCache(lines)
	if info.cacheType != "hit" {
		t.Errorf("expected hit, got %s", info.cacheType)
	}
	if info.hash != hash {
		t.Errorf("expected hash %s, got %s", hash, info.hash)
	}
	if info.scope != "30m/4f" {
		t.Errorf("expected scope 30m/4f, got %q", info.scope)
	}
	if info.risk != "low" {
		t.Errorf("expected risk low, got %q", info.risk)
	}
}

func TestParseSweepCacheStaleHash(t *testing.T) {
	lines := []string{
		"2026-04-27T10:00Z claude note sweep-assess: not-picked hash:000000000000 scope:30m risk:low",
	}
	info := parseSweepCache(lines)
	// parseSweepCache returns the stored hash; caller compares with current hash.
	if info.hash != "000000000000" {
		t.Errorf("expected stored hash 000000000000, got %q", info.hash)
	}
}

func TestParseSweepCacheSkip(t *testing.T) {
	hash := bodyHash("Body.\n")
	lines := []string{
		"2026-04-27T10:00Z claude note sweep-skip: status-needs-human hash:" + hash,
	}
	info := parseSweepCache(lines)
	if info.cacheType != "skip" {
		t.Errorf("expected skip, got %s", info.cacheType)
	}
}

func TestParseSweepCacheSkipExpired(t *testing.T) {
	hash := bodyHash("Body.\n")
	// expires in the past → must demote to miss
	lines := []string{
		"2026-04-01T10:00Z claude note sweep-skip: cooldown-24h hash:" + hash + " expires:2026-04-01T11:00",
	}
	info := parseSweepCache(lines)
	if info.cacheType != "miss" {
		t.Errorf("expected miss for expired skip, got %s", info.cacheType)
	}
}

func TestParseSweepCacheSkipNotExpired(t *testing.T) {
	hash := bodyHash("Body.\n")
	// expires far in the future → still skip
	lines := []string{
		"2099-01-01T00:00Z claude note sweep-skip: cooldown-24h hash:" + hash + " expires:2099-12-31T23:59",
	}
	info := parseSweepCache(lines)
	if info.cacheType != "skip" {
		t.Errorf("expected skip for non-expired line, got %s", info.cacheType)
	}
}

// ---------------------------------------------------------------------------
// cmdSweepWrite
// ---------------------------------------------------------------------------

func captureStdout(fn func()) string {
	old := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w
	fn()
	w.Close()
	os.Stdout = old
	out, _ := io.ReadAll(r)
	return string(out)
}

func ergWithLog(id string, logLines []string) string {
	var sb strings.Builder
	sb.WriteString("%erg v1\n")
	sb.WriteString("Title: test " + id + "\n")
	sb.WriteString("Status: open\n")
	sb.WriteString("Created: 2026-04-26\n")
	sb.WriteString("Author: test\n")
	sb.WriteString("\n--- log ---\n")
	for _, l := range logLines {
		sb.WriteString(l + "\n")
	}
	sb.WriteString("\n--- body ---\n")
	sb.WriteString("Core body.\n")
	return sb.String()
}

func TestCmdSweepWriteWrites(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "0001-alpha.erg")
	if err := os.WriteFile(path, []byte(ergWithLog("0001", nil)), 0644); err != nil {
		t.Fatal(err)
	}

	out := captureStdout(func() {
		cmdSweepWrite([]string{path, "not-picked", "30m/4f", "low", "riper ticket available"})
	})
	if !strings.Contains(out, "WROTE") {
		t.Errorf("expected WROTE, got %q", out)
	}

	// File should now contain the assessment section and log line.
	raw, _ := os.ReadFile(path)
	content := string(raw)
	if !strings.Contains(content, "## Picker assessment") {
		t.Error("assessment section not written to body")
	}
	if !strings.Contains(content, "sweep-assess:") {
		t.Error("sweep-assess log line not written")
	}
}

func TestCmdSweepWriteCached(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "0001-alpha.erg")

	// Pre-compute hash for "Core body.\n"
	hash := bodyHash("Core body.\n")
	logLines := []string{
		"2026-04-26T00:00Z claude created",
		"2026-04-27T10:00Z claude note sweep-assess: not-picked hash:" + hash + " scope:30m risk:low",
	}
	if err := os.WriteFile(path, []byte(ergWithLog("0001", logLines)), 0644); err != nil {
		t.Fatal(err)
	}

	out := captureStdout(func() {
		cmdSweepWrite([]string{path, "not-picked", "30m", "low", "same as before"})
	})
	if !strings.Contains(out, "CACHED") {
		t.Errorf("expected CACHED, got %q", out)
	}

	// File must not have changed.
	raw, _ := os.ReadFile(path)
	if strings.Contains(string(raw), "## Picker assessment") {
		t.Error("assessment section written despite cache hit")
	}
}

func TestCmdSweepWriteHashStableAfterWrite(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "0001-alpha.erg")
	if err := os.WriteFile(path, []byte(ergWithLog("0001", nil)), 0644); err != nil {
		t.Fatal(err)
	}

	// First write.
	captureStdout(func() {
		cmdSweepWrite([]string{path, "not-picked", "30m", "low", "reason A"})
	})

	// Second write on same body — must be CACHED (hash unchanged after first write).
	out := captureStdout(func() {
		cmdSweepWrite([]string{path, "not-picked", "30m", "low", "reason B"})
	})
	if !strings.Contains(out, "CACHED") {
		t.Errorf("expected CACHED on second write, got %q", out)
	}
}

// ---------------------------------------------------------------------------
// TestCmdValidateFileArgCycleDetected ensures that a mutual dependency cycle
// (0001 → 0002 → 0001) is detected even when only 0001's file is passed.
func TestCmdValidateFileArgCycleDetected(t *testing.T) {
	dir := t.TempDir()

	// Write both tickets to the same directory
	f1 := filepath.Join(dir, "0001-alpha.erg")
	f2 := filepath.Join(dir, "0002-beta.erg")
	if err := os.WriteFile(f1, []byte(minimalErg("0001", "alpha", []string{"0002"})), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(f2, []byte(minimalErg("0002", "beta", []string{"0001"})), 0644); err != nil {
		t.Fatal(err)
	}

	// Pass only 0001's file — cycle should still be detected via context dir load
	exit, out := captureValidate([]string{f1})
	if exit == 0 {
		t.Errorf("expected non-zero exit code (cycle), got 0; output: %s", out)
	}
	if !strings.Contains(out, "dependency cycle") {
		t.Errorf("expected 'dependency cycle' in output, got: %s", out)
	}
}

// TestCmdValidateFileArgValidRefNoFalsePositive ensures that a valid Blocked-by
// reference to a sibling ticket does not produce a false "unknown ticket ID"
// error when only one file is passed.
func TestCmdValidateFileArgValidRefNoFalsePositive(t *testing.T) {
	dir := t.TempDir()

	// 0001 depends on 0002; 0002 has no deps — no cycle, valid ref
	f1 := filepath.Join(dir, "0001-alpha.erg")
	f2 := filepath.Join(dir, "0002-beta.erg")
	if err := os.WriteFile(f1, []byte(minimalErg("0001", "alpha", []string{"0002"})), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(f2, []byte(minimalErg("0002", "beta", nil)), 0644); err != nil {
		t.Fatal(err)
	}

	// Pass only 0001's file — should PASS (0002 is loaded as context)
	exit, out := captureValidate([]string{f1})
	if exit != 0 {
		t.Errorf("expected exit 0 (valid ref), got %d; output: %s", exit, out)
	}
}

// ---------------------------------------------------------------------------
// sweep-skip / appendToTicket: body must not be mutated by slice aliasing
// ---------------------------------------------------------------------------

// captureSweepSkip runs cmdSweepSkip(args) and returns exit code + stdout.
func captureSweepSkip(args []string) (int, string) {
	old := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w
	exit := cmdSweepSkip(args)
	w.Close()
	os.Stdout = old
	out, _ := io.ReadAll(r)
	return exit, string(out)
}

// TestSweepSkipPreservesBody guards against the slice-aliasing bug in
// cmdSweepSkip where `beforeBody := raw[:idx]` shared the backing array
// with the bytes from os.ReadFile and a subsequent append corrupted the
// body. A correct implementation leaves the body byte-identical and
// keeps exactly one `--- body ---` separator.
func TestSweepSkipPreservesBody(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "0001-roundtrip.erg")
	body := "## Context\n\nThis body must survive sweep-skip without a single byte changed.\n" +
		"It is long enough that any aliasing append from cmdSweepSkip would visibly\n" +
		"overwrite the start of the body section.\n\n## Actions\n1. Round-trip.\n"
	original := minimalErg("0001", "roundtrip", nil)
	// Replace the placeholder body with our long body.
	original = strings.Replace(original, "Test body.\n", body, 1)
	if err := os.WriteFile(path, []byte(original), 0644); err != nil {
		t.Fatal(err)
	}

	exit, out := captureSweepSkip([]string{path, "scope-too-large", "expires:2026-12-31T00:00Z"})
	if exit != 0 {
		t.Fatalf("sweep-skip exit %d, stdout=%q", exit, out)
	}

	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	gotStr := string(got)

	sepCount := strings.Count(gotStr, "\n--- body ---\n")
	if sepCount != 1 {
		t.Errorf("expected exactly one '--- body ---' separator, got %d", sepCount)
	}

	idx := strings.Index(gotStr, "\n--- body ---\n")
	if idx < 0 {
		t.Fatal("no '--- body ---' separator found")
	}
	gotBody := gotStr[idx+len("\n--- body ---\n"):]
	if gotBody != body {
		t.Errorf("body corrupted by sweep-skip\nwant: %q\n got: %q", body, gotBody)
	}
}

// TestAppendToTicketPreservesBody confirms appendToTicket (used by
// cmdSweepWrite) does not corrupt body content via slice aliasing.
func TestAppendToTicketPreservesBody(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "0002-append.erg")
	body := "## Context\n\nAppendToTicket must leave existing body bytes intact and\n" +
		"only add the new section at the tail.\n"
	original := minimalErg("0002", "append", nil)
	original = strings.Replace(original, "Test body.\n", body, 1)
	if err := os.WriteFile(path, []byte(original), 0644); err != nil {
		t.Fatal(err)
	}

	logLine := "2026-04-29T10:00Z test note sweep-pick: picked hash:abcdef012345 scope:S risk:R"
	addition := "## Picker assessment 2026-04-29T10:00Z\n**Decision:** picked\n"
	if err := appendToTicket(path, logLine, addition); err != nil {
		t.Fatal(err)
	}

	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	gotStr := string(got)

	if c := strings.Count(gotStr, "\n--- body ---\n"); c != 1 {
		t.Errorf("expected exactly one '--- body ---' separator, got %d", c)
	}
	if !strings.Contains(gotStr, body) {
		t.Errorf("original body content missing from result:\n%s", gotStr)
	}
	if !strings.Contains(gotStr, logLine) {
		t.Errorf("new log line missing")
	}
	if !strings.Contains(gotStr, addition) {
		t.Errorf("new body section missing")
	}
}
