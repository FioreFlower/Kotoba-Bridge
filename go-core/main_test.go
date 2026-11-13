package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"
)

type transportFunc func(*http.Request) (*http.Response, error)

func (f transportFunc) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }
func configured() *Core                                                   { c := NewCore(); c.configured = true; return c }
func TestObserve(t *testing.T) {
	c := configured()
	now := time.Unix(100, 0)
	c.now = func() time.Time { return now }
	if c.observe("こんにちは。", false) != "" {
		t.Fatal("early")
	}
	now = now.Add(time.Second)
	if c.observe("こんにちは。", false) != "こんにちは。" {
		t.Fatal("not stable")
	}
	if c.observe("こんにちは。", false) != "" {
		t.Fatal("duplicate")
	}
	c.observe("", false)
	c.observe("こんにちは。", false)
	now = now.Add(time.Second)
	if c.observe("こんにちは。", false) == "" {
		t.Fatal("blank reset failed")
	}
}
func TestBudgetAndConfigure(t *testing.T) {
	c := configured()
	now := time.Unix(100, 0)
	c.now = func() time.Time { return now }
	if _, e := c.translate("こんにちは。"); e != nil {
		t.Fatal(e)
	}
	if _, e := c.translate("different"); e == nil {
		t.Fatal("interval")
	}
	if _, e := c.handle(Request{Version: 1, Method: "configure", Demo: true}); e != nil {
		t.Fatal(e)
	}
	if c.calls != 1 || c.chars != 6 {
		t.Fatal("configure reset budget", c.calls, c.chars)
	}
	c.calls = 100
	now = now.Add(4 * time.Second)
	if _, e := c.translate("blocked"); e == nil {
		t.Fatal("call limit")
	}
}
func TestPayloadAndResponse(t *testing.T) {
	c := configured()
	c.demo = false
	c.key = "not-real"
	c.history = []string{"前の台詞"}
	c.client = &http.Client{Transport: transportFunc(func(r *http.Request) (*http.Response, error) {
		if r.URL.String() != "https://api-free.deepl.com/v2/translate" {
			t.Fatal(r.URL)
		}
		var p map[string]any
		json.NewDecoder(r.Body).Decode(&p)
		if p["source_lang"] != "JA" || p["target_lang"] != "KO" || p["context"] != "前の台詞" {
			t.Fatal(p)
		}
		if _, ok := p["image"]; ok {
			t.Fatal("image transmitted")
		}
		return &http.Response{StatusCode: 200, Body: io.NopCloser(strings.NewReader(`{"translations":[{"text":"안녕하세요."}]}`))}, nil
	})}
	if out, e := c.translate("こんにちは。"); e != nil || out != "안녕하세요." {
		t.Fatal(out, e)
	}
}
func TestFailuresReserveAndRedact(t *testing.T) {
	c := configured()
	c.demo = false
	c.key = "secret"
	c.client = &http.Client{Transport: transportFunc(func(*http.Request) (*http.Response, error) { return nil, errors.New("secret-key") })}
	_, e := c.translate("hello")
	if e == nil || strings.Contains(e.Error(), "secret") || c.calls != 1 || c.chars != 5 {
		t.Fatal("failure state", e, c.calls, c.chars)
	}
}
func TestHTTPAndMalformed(t *testing.T) {
	for _, code := range []int{403, 429, 456, 500, 302} {
		c := configured()
		c.demo = false
		c.key = "secret"
		c.client = &http.Client{Transport: transportFunc(func(*http.Request) (*http.Response, error) {
			return &http.Response{StatusCode: code, Body: io.NopCloser(strings.NewReader("secret"))}, nil
		})}
		if _, e := c.translate("hello"); e == nil || strings.Contains(e.Error(), "secret") {
			t.Fatal(code, e)
		}
	}
	c := configured()
	c.demo = false
	c.key = "test"
	c.client = &http.Client{Transport: transportFunc(func(*http.Request) (*http.Response, error) {
		return &http.Response{StatusCode: 200, Body: io.NopCloser(strings.NewReader(`{"wrong":1}`))}, nil
	})}
	if _, e := c.translate("hello"); e == nil {
		t.Fatal("malformed accepted")
	}
}
func TestProtocol(t *testing.T) {
	var output bytes.Buffer
	input := `{"id":1,"version":1,"method":"hello"}` + "\n" + `{"id":2,"version":9,"method":"hello"}` + "\n" + `{"id":3,"version":1,"method":"shutdown"}` + "\n"
	if e := serve(strings.NewReader(input), &output, NewCore()); e != nil {
		t.Fatal(e)
	}
	lines := strings.Split(strings.TrimSpace(output.String()), "\n")
	if len(lines) != 3 {
		t.Fatal(output.String())
	}
	var first, second Response
	json.Unmarshal([]byte(lines[0]), &first)
	json.Unmarshal([]byte(lines[1]), &second)
	if !first.OK || second.OK {
		t.Fatal(output.String())
	}
}
func TestValidation(t *testing.T) {
	c := NewCore()
	if _, e := c.handle(Request{Version: 1, Method: "configure"}); e == nil {
		t.Fatal("empty key")
	}
	c.configured = true
	if _, e := c.translate(strings.Repeat("猫", 2001)); e == nil {
		t.Fatal("oversize")
	}
	if _, e := recognize("bad base64", "tesseract"); e == nil {
		t.Fatal("bad image")
	}
	if c.calls != 0 {
		t.Fatal("invalid reserved")
	}
}
func TestCacheAndClear(t *testing.T) {
	c := configured()
	if _, e := c.translate("こんにちは。"); e != nil {
		t.Fatal(e)
	}
	c.history = nil
	if _, e := c.translate("こんにちは。"); e != nil {
		t.Fatal("cache missed", e)
	}
	if c.calls != 1 {
		t.Fatal("cache cost")
	}
	c.clear()
	if len(c.cache) != 0 || c.calls != 1 {
		t.Fatal("clear")
	}
}
