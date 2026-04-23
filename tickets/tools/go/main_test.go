package main

import (
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
