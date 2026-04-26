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
