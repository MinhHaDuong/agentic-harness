package main

import (
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
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

// minimalErgWithStatus is like minimalErg but with a custom status value.
func minimalErgWithStatus(id, status string) string {
	var sb strings.Builder
	sb.WriteString("%erg v1\n")
	sb.WriteString("Title: test ticket " + id + "\n")
	sb.WriteString("Status: " + status + "\n")
	sb.WriteString("Created: 2026-04-26\n")
	sb.WriteString("Author: test\n")
	sb.WriteString("\n--- log ---\n")
	sb.WriteString("2026-04-26T00:00Z test created\n")
	sb.WriteString("\n--- body ---\n")
	sb.WriteString("Test body.\n")
	return sb.String()
}

// ---------------------------------------------------------------------------
// Validator: Status enum
// ---------------------------------------------------------------------------

func TestValidatorRejectsDoing(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "0001-alpha.erg")
	if err := os.WriteFile(path, []byte(minimalErgWithStatus("0001", "doing")), 0644); err != nil {
		t.Fatal(err)
	}
	exit, out := captureValidate([]string{path})
	if exit == 0 {
		t.Fatalf("expected non-zero exit for Status: doing, got 0; output: %s", out)
	}
	if !strings.Contains(out, "doing") {
		t.Errorf("expected 'doing' in error output, got: %s", out)
	}
}

func TestValidatorRejectsPending(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "0001-alpha.erg")
	if err := os.WriteFile(path, []byte(minimalErgWithStatus("0001", "pending")), 0644); err != nil {
		t.Fatal(err)
	}
	exit, out := captureValidate([]string{path})
	if exit == 0 {
		t.Fatalf("expected non-zero exit for Status: pending, got 0; output: %s", out)
	}
	if !strings.Contains(out, "pending") {
		t.Errorf("expected 'pending' in error output, got: %s", out)
	}
}

func TestValidatorAcceptsOpenAndClosed(t *testing.T) {
	dir := t.TempDir()
	for _, status := range []string{"open", "closed"} {
		path := filepath.Join(dir, "0001-alpha.erg")
		if err := os.WriteFile(path, []byte(minimalErgWithStatus("0001", status)), 0644); err != nil {
			t.Fatal(err)
		}
		exit, out := captureValidate([]string{path})
		if exit != 0 {
			t.Errorf("Status: %s should be valid, got exit %d; output: %s", status, exit, out)
		}
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
// Separator uniqueness
// ---------------------------------------------------------------------------

// TestValidateRejectsDuplicateBodySeparator guards rule 11: a ticket with
// more than one `--- body ---` separator must fail validation.
func TestValidateRejectsDuplicateBodySeparator(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "0001-dup.erg")
	content := "%erg v1\n" +
		"Title: dup body sep\n" +
		"Status: open\n" +
		"Created: 2026-04-29\n" +
		"Author: test\n" +
		"\n--- log ---\n" +
		"2026-04-29T00:00Z test created\n" +
		"--- body ---\n" +
		"first body line\n" +
		"--- body ---\n" +
		"after the duplicate separator\n"
	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}

	exit, out := captureValidate([]string{path})
	if exit == 0 {
		t.Fatalf("expected validate to fail, got exit 0; output: %s", out)
	}
	if !strings.Contains(out, "--- body ---") || !strings.Contains(out, "expected 1") {
		t.Errorf("error message missing duplicate-separator detail: %s", out)
	}
}

// TestValidateRejectsDuplicateLogSeparator covers the symmetric case for
// the `--- log ---` separator.
func TestValidateRejectsDuplicateLogSeparator(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "0001-duplog.erg")
	content := "%erg v1\n" +
		"Title: dup log sep\n" +
		"Status: open\n" +
		"Created: 2026-04-29\n" +
		"Author: test\n" +
		"\n--- log ---\n" +
		"2026-04-29T00:00Z test created\n" +
		"--- log ---\n" +
		"2026-04-29T00:01Z test note duplicate\n" +
		"--- body ---\n" +
		"body\n"
	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}

	exit, out := captureValidate([]string{path})
	if exit == 0 {
		t.Fatalf("expected validate to fail, got exit 0; output: %s", out)
	}
	if !strings.Contains(out, "--- log ---") || !strings.Contains(out, "expected 1") {
		t.Errorf("error message missing duplicate-separator detail: %s", out)
	}
}

// ---------------------------------------------------------------------------
// hasBranch — git branch claim-check
// ---------------------------------------------------------------------------

// runGit runs a git command in dir and fails the test if the command errors.
func runGit(t *testing.T, dir string, args ...string) {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("git %s in %s failed: %v\n%s", strings.Join(args, " "), dir, err, out)
	}
}

// newGitRepo creates a fresh temp git repo, configures user identity, and
// chdirs into it. The returned cleanup restores the original cwd. Tests that
// use this helper must not run in parallel — they all mutate process cwd.
func newGitRepo(t *testing.T) (string, func()) {
	t.Helper()
	repo := t.TempDir()
	runGit(t, repo, "init", "-q", "-b", "main")
	runGit(t, repo, "config", "user.email", "test@example.com")
	runGit(t, repo, "config", "user.name", "test")
	runGit(t, repo, "config", "commit.gpgsign", "false")
	runGit(t, repo, "config", "tag.gpgsign", "false")
	runGit(t, repo, "commit", "--allow-empty", "-q", "-m", "init")

	prev, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	if err := os.Chdir(repo); err != nil {
		t.Fatalf("chdir to %s: %v", repo, err)
	}
	cleanup := func() {
		if err := os.Chdir(prev); err != nil {
			t.Errorf("restore cwd to %s: %v", prev, err)
		}
	}
	t.Cleanup(cleanup)
	return repo, cleanup
}

// TestHasBranchLocalMatch covers the happy path: a local branch whose name
// contains the 4-digit ticket ID makes hasBranch return true.
func TestHasBranchLocalMatch(t *testing.T) {
	repo, _ := newGitRepo(t)
	runGit(t, repo, "checkout", "-q", "-b", "0099-foo")

	if !hasBranch("0099") {
		t.Errorf("hasBranch(\"0099\") = false, want true (branch 0099-foo exists locally)")
	}
}

// TestHasBranchLocalNoMatch covers two negative cases:
//   1. No matching branch exists in a fresh repo.
//   2. A matching branch existed but was deleted — hasBranch must return
//      false again afterwards.
func TestHasBranchLocalNoMatch(t *testing.T) {
	repo, _ := newGitRepo(t)

	// Pre-creation: nothing matches 0098.
	if hasBranch("0098") {
		t.Errorf("hasBranch(\"0098\") = true before any branch created, want false")
	}

	// Create then delete a matching branch; final state must report false.
	runGit(t, repo, "checkout", "-q", "-b", "0098-bar")
	runGit(t, repo, "checkout", "-q", "main")
	runGit(t, repo, "branch", "-q", "-D", "0098-bar")

	if hasBranch("0098") {
		t.Errorf("hasBranch(\"0098\") = true after branch deleted, want false")
	}
}

// TestHasBranchRemoteMatch verifies that a branch which exists only on a
// remote (origin/0099-baz) is detected via the `git branch -r` fallback.
func TestHasBranchRemoteMatch(t *testing.T) {
	root := t.TempDir()
	bare := filepath.Join(root, "bare.git")
	clone := filepath.Join(root, "clone")

	if err := os.MkdirAll(bare, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(clone, 0755); err != nil {
		t.Fatal(err)
	}

	runGit(t, bare, "init", "-q", "--bare", "-b", "main")

	runGit(t, clone, "init", "-q", "-b", "main")
	runGit(t, clone, "config", "user.email", "test@example.com")
	runGit(t, clone, "config", "user.name", "test")
	runGit(t, clone, "config", "commit.gpgsign", "false")
	runGit(t, clone, "config", "tag.gpgsign", "false")
	runGit(t, clone, "commit", "--allow-empty", "-q", "-m", "init")
	runGit(t, clone, "remote", "add", "origin", bare)
	runGit(t, clone, "checkout", "-q", "-b", "0099-baz")
	runGit(t, clone, "push", "-q", "origin", "0099-baz")
	// Move local HEAD off the matching branch and delete it locally so the
	// only place 0099 lives is on origin.
	runGit(t, clone, "checkout", "-q", "main")
	runGit(t, clone, "branch", "-q", "-D", "0099-baz")
	runGit(t, clone, "fetch", "-q", "origin")

	prev, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	t.Cleanup(func() {
		if err := os.Chdir(prev); err != nil {
			t.Errorf("restore cwd: %v", err)
		}
	})
	if err := os.Chdir(clone); err != nil {
		t.Fatalf("chdir clone: %v", err)
	}

	if !hasBranch("0099") {
		t.Errorf("hasBranch(\"0099\") = false, want true (origin/0099-baz exists)")
	}
}

// TestHasBranchOfflineFallback verifies that when there is no remote
// configured (so `git branch -r` returns empty / does not error in a way
// that propagates), hasBranch returns false rather than panicking. This
// guards the offline-safe contract documented above the function.
func TestHasBranchOfflineFallback(t *testing.T) {
	defer func() {
		if r := recover(); r != nil {
			t.Errorf("hasBranch panicked on offline/no-remote repo: %v", r)
		}
	}()

	newGitRepo(t)
	if hasBranch("0099") {
		t.Errorf("hasBranch(\"0099\") = true on empty no-remote repo, want false")
	}
}

// ---------------------------------------------------------------------------
// closeTicket — erg close subcommand (ticket 0078)
// ---------------------------------------------------------------------------

// TestCmdCloseOpenTicket: closing an open ticket sets Status: closed and
// appends a `claude status closed — <reason>` log line with a UTC minute
// timestamp.
func TestCmdCloseOpenTicket(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "0001-alpha.erg")
	if err := os.WriteFile(path, []byte(minimalErgWithStatus("0001", "open")), 0644); err != nil {
		t.Fatal(err)
	}

	exit, msg := closeTicket(dir, "0001", "done")
	if exit != 0 {
		t.Fatalf("expected exit 0, got %d (msg: %s)", exit, msg)
	}
	if !strings.Contains(msg, "closed 0001") {
		t.Errorf("expected success message to mention closed 0001, got: %s", msg)
	}

	parsed := parseErg(path)
	if parsed.Status() != "closed" {
		t.Errorf("expected Status: closed, got %q", parsed.Status())
	}

	// The last log line should match the status-closed pattern.
	if len(parsed.LogLines) == 0 {
		t.Fatalf("expected at least one log line, got 0")
	}
	last := parsed.LogLines[len(parsed.LogLines)-1]
	wantRE := regexp.MustCompile(`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z claude status closed — done$`)
	if !wantRE.MatchString(last) {
		t.Errorf("last log line %q did not match expected pattern", last)
	}
}

// TestCmdCloseIdempotent: closing an already-closed ticket does not append
// another log line and returns exit 0.
func TestCmdCloseIdempotent(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "0001-alpha.erg")
	if err := os.WriteFile(path, []byte(minimalErgWithStatus("0001", "closed")), 0644); err != nil {
		t.Fatal(err)
	}

	before := parseErg(path)
	beforeCount := len(before.LogLines)

	exit, msg := closeTicket(dir, "0001", "done")
	if exit != 0 {
		t.Fatalf("expected exit 0 on idempotent close, got %d (msg: %s)", exit, msg)
	}
	if !strings.Contains(msg, "already closed") {
		t.Errorf("expected idempotent message to mention 'already closed', got: %s", msg)
	}

	after := parseErg(path)
	afterCount := len(after.LogLines)
	if afterCount != beforeCount {
		t.Errorf("expected log line count unchanged (%d), got %d", beforeCount, afterCount)
	}
	if after.Status() != "closed" {
		t.Errorf("Status should remain closed, got %q", after.Status())
	}
}

// TestCmdCloseMissingID: closing a non-existent ticket returns non-zero.
func TestCmdCloseMissingID(t *testing.T) {
	dir := t.TempDir()
	exit, msg := closeTicket(dir, "9999", "done")
	if exit == 0 {
		t.Fatalf("expected non-zero exit for missing id, got 0 (msg: %s)", msg)
	}
	if !strings.Contains(msg, "9999") {
		t.Errorf("expected error to mention id 9999, got: %s", msg)
	}
}

// TestCmdCloseDefaultReason: when closeTicket is called with an empty
// reason, it falls back to defaultCloseReason ("done") and the resulting
// log line ends in `— done`. This covers the cmdClose dispatch default
// without forcing a chdir.
func TestCmdCloseDefaultReason(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "0001-alpha.erg")
	if err := os.WriteFile(path, []byte(minimalErgWithStatus("0001", "open")), 0644); err != nil {
		t.Fatal(err)
	}

	// Empty reason → must default to "done".
	exit, _ := closeTicket(dir, "0001", "")
	if exit != 0 {
		t.Fatalf("expected exit 0, got %d", exit)
	}
	if defaultCloseReason != "done" {
		t.Errorf("expected defaultCloseReason 'done', got %q", defaultCloseReason)
	}

	parsed := parseErg(path)
	if len(parsed.LogLines) == 0 {
		t.Fatalf("expected at least one log line")
	}
	last := parsed.LogLines[len(parsed.LogLines)-1]
	if !strings.HasSuffix(last, "— done") {
		t.Errorf("last log line should end with '— done', got: %q", last)
	}
}
