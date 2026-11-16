package main

import (
	"errors"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"
)

func TestUsageEndpointsAndNoSessionAccounting(t *testing.T) {
	for _, pro := range []bool{false, true} {
		c := NewCore()
		c.configured = true
		c.demo = false
		c.provider = "deepl"
		c.key = "synthetic-key"
		c.pro = pro
		c.client = &http.Client{Transport: transportFunc(func(r *http.Request) (*http.Response, error) {
			host := "api-free.deepl.com"
			if pro {
				host = "api.deepl.com"
			}
			if r.Method != "GET" || r.URL.Host != host || r.URL.Path != "/v2/usage" || r.Header.Get("Authorization") != "DeepL-Auth-Key synthetic-key" {
				t.Fatal("wrong request")
			}
			return &http.Response{StatusCode: 200, Body: io.NopCloser(strings.NewReader(`{"character_count":120,"character_limit":1000000000000,"api_key_character_count":12,"api_key_character_limit":500}`))}, nil
		})}
		u, e := c.usage()
		if e != nil || *u.CharacterCount != 120 || *u.CharacterLimit != 1000000000000 || u.CheckedAt == "" || c.calls != 0 || c.chars != 0 {
			t.Fatal(u, e)
		}
		if _, e = c.usage(); e == nil {
			t.Fatal("rate limit missing")
		}
	}
}
func TestUsageForbiddenModesAndSanitizedFailure(t *testing.T) {
	for _, mode := range []string{"demo", "local", "missing"} {
		c := NewCore()
		c.configured = true
		c.key = "synthetic"
		c.demo = mode == "demo"
		c.provider = mode
		if mode == "missing" {
			c.key = ""
		}
		c.client = &http.Client{Transport: transportFunc(func(*http.Request) (*http.Response, error) { t.Fatal("unexpected network"); return nil, nil })}
		if _, e := c.usage(); e == nil {
			t.Fatal("mode permitted")
		}
	}
	c := NewCore()
	c.configured = true
	c.demo = false
	c.key = "private"
	now := time.Now()
	c.now = func() time.Time { return now }
	calls := 0
	c.client = &http.Client{Transport: transportFunc(func(*http.Request) (*http.Response, error) { calls++; return nil, errors.New("private") })}
	_, e := c.usage()
	if e == nil || strings.Contains(e.Error(), "private") {
		t.Fatal(e)
	}
	c.usage()
	if calls != 1 {
		t.Fatal("failure retried")
	}
	now = now.Add(time.Minute)
	c.usage()
	if calls != 2 {
		t.Fatal("refresh blocked")
	}
}
func TestUsageOptionalLimitAndBadResponses(t *testing.T) {
	for _, body := range []string{`{}`, `{"character_count":-1}`, `{"character_count":1.2}`, `{"character_count":1,"character_limit":-2}`, strings.Repeat("x", maxResponse+1)} {
		c := NewCore()
		c.configured = true
		c.demo = false
		c.key = "synthetic"
		c.client = &http.Client{Transport: transportFunc(func(*http.Request) (*http.Response, error) {
			return &http.Response{StatusCode: 200, Body: io.NopCloser(strings.NewReader(body))}, nil
		})}
		if _, e := c.usage(); e == nil {
			t.Fatal("bad response accepted")
		}
	}
	c := NewCore()
	c.configured = true
	c.demo = false
	c.key = "synthetic"
	c.client = &http.Client{Transport: transportFunc(func(*http.Request) (*http.Response, error) {
		return &http.Response{StatusCode: 200, Body: io.NopCloser(strings.NewReader(`{"character_count":0}`))}, nil
	})}
	u, e := c.usage()
	if e != nil || u.CharacterLimit != nil {
		t.Fatal(u, e)
	}
}
