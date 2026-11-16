package main

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strconv"
	"strings"
	"testing"
)

func TestLocalPayload(t *testing.T) {
	count := 0
	s := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		count++
		if r.URL.Path != "/v1/chat/completions" || r.Header.Get("Authorization") != "" {
			t.Error("path or key leak")
		}
		var p map[string]any
		json.NewDecoder(r.Body).Decode(&p)
		if p["stream"] != false || p["model"] != "kotoba-local" {
			t.Error(p)
		}
		messages := p["messages"].([]any)
		if !strings.Contains(messages[1].(map[string]any)["content"].(string), "くそ") {
			t.Error("source changed")
		}
		io.WriteString(w, `{"choices":[{"finish_reason":"stop","message":{"content":"젠장, 도망쳐!"}}]}`)
	}))
	defer s.Close()
	u, _ := url.Parse(s.URL)
	port, _ := strconv.Atoi(u.Port())
	c := NewCore()
	c.key = "synthetic-cloud-secret"
	_, e := c.handle(Request{Version: 1, Method: "configure", Provider: "local", LocalPort: port, LocalModel: "kotoba-local"})
	if e != nil {
		t.Fatal(e)
	}
	if c.key != "" {
		t.Fatal("cloud key retained")
	}
	out, e := c.translate("くそ、逃げろ！")
	if e != nil || out != "젠장, 도망쳐!" || count != 1 {
		t.Fatal(out, e, count)
	}
}
func TestLocalFailureNoFallback(t *testing.T) {
	for _, body := range []string{`{"choices":[{"finish_reason":"length","message":{"content":"partial"}}]}`, `{"choices":[{"finish_reason":"stop","message":{"content":"","refusal":"no"}}]}`, `{"choices":[]}`, `{"choices":[{"finish_reason":"stop","message":{"content":"ok","tool_calls":[{}]}}]}`, strings.Repeat("x", 65537)} {
		c := NewCore()
		c.configured = true
		c.demo = false
		c.provider = "local"
		c.localPort = 8087
		c.localModel = "kotoba-local"
		n := 0
		c.localHTTP = &http.Client{Transport: transportFunc(func(r *http.Request) (*http.Response, error) {
			n++
			return &http.Response{StatusCode: 200, Body: io.NopCloser(strings.NewReader(body))}, nil
		})}
		c.client = &http.Client{Transport: transportFunc(func(r *http.Request) (*http.Response, error) { t.Fatal("cloud fallback"); return nil, nil })}
		if _, e := c.translate("合成の台詞"); e == nil || n != 1 || len(c.cache) != 0 || len(c.history) != 0 {
			t.Fatal(e, n)
		}
	}
}
func TestLocalNetworkBoundary(t *testing.T) {
	client := localClient()
	if client.CheckRedirect(nil, nil) == nil {
		t.Fatal("redirect")
	}
	tr := client.Transport.(*http.Transport)
	if tr.Proxy != nil {
		t.Fatal("proxy")
	}
	if _, e := tr.DialContext(context.Background(), "tcp", "example.com:80"); e == nil {
		t.Fatal("remote")
	}
	for _, m := range []string{"../model", "cloud:model", "http://host", "a b", ""} {
		if validLocal(8087, m) {
			t.Fatal(m)
		}
	}
	c := NewCore()
	for _, r := range []Request{{Provider: "unknown"}, {Provider: "local", LocalPort: 80, LocalModel: "m"}, {Provider: "local", LocalPort: 8087, LocalModel: "m", Key: "secret"}} {
		r.Version = 1
		r.Method = "configure"
		if _, e := c.handle(r); e == nil {
			t.Fatal(r)
		}
	}
}

func TestLocalNoArtificialCloudDelay(t *testing.T) {
	c := NewCore()
	c.provider = "local"
	c.last = c.now()
	result, err := c.handle(Request{Version: 1, Method: "status"})
	if err != nil || result.(map[string]any)["retry_after_ms"] != int64(0) {
		t.Fatal(result, err)
	}
	c.provider = "deepl"
	result, _ = c.handle(Request{Version: 1, Method: "status"})
	if result.(map[string]any)["retry_after_ms"].(int64) <= 0 {
		t.Fatal("cloud rate gate lost")
	}
}

func TestLocalTokenValidation(t *testing.T) {
	for _, token := range []string{"x", strings.Repeat("a", 63), strings.Repeat("a", 63) + "\n"} {
		if validLocalToken(token) {
			t.Fatal("accepted invalid local token")
		}
	}
	if !validLocalToken("") || !validLocalToken(strings.Repeat("a", 64)) {
		t.Fatal("valid local token rejected")
	}
}

func TestManagedAuthenticationAndClear(t *testing.T) {
	token := strings.Repeat("b", 64)
	c := NewCore()
	_, err := c.handle(Request{Version: 1, Method: "configure", Provider: "local", LocalPort: 8087, LocalModel: "managed", LocalToken: token})
	if err != nil {
		t.Fatal(err)
	}
	c.localHTTP = &http.Client{Transport: transportFunc(func(r *http.Request) (*http.Response, error) {
		if r.Header.Get("Authorization") != "Bearer "+token {
			t.Error("missing session authentication")
		}
		return &http.Response{StatusCode: 200, Body: io.NopCloser(strings.NewReader(`{"choices":[{"finish_reason":"stop","message":{"content":"안녕"}}]}`))}, nil
	})}
	if _, err = c.requestLocal("こんにちは", ""); err != nil {
		t.Fatal(err)
	}
	if _, err = c.handle(Request{Version: 1, Method: "configure", Demo: true}); err != nil {
		t.Fatal(err)
	}
	if c.localToken != "" {
		t.Fatal("session token retained in demo")
	}
}
