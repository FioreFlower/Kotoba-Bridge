package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"image"
	"image/png"
	"io"
	"net/http"
	"os"
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

func TestConfigureRejectsInvalidKeyWithoutChangingSession(t *testing.T) {
	c := configured()
	c.key = "existing-key"
	c.calls = 7
	for _, key := range []string{" ", "\t", "key\r\nHeader:value", strings.Repeat("x", 4097)} {
		_, err := c.handle(Request{Version: 1, Method: "configure", Key: key})
		if err == nil || c.key != "existing-key" || c.calls != 7 {
			t.Fatalf("invalid key changed session")
		}
	}
	if _, err := c.handle(Request{Version: 1, Method: "configure", Key: ""}); err != nil {
		t.Fatal("omitted key should preserve", err)
	}
	if c.key != "existing-key" {
		t.Fatal("key lost")
	}
}

func TestForgetKeyRetainsBudgetAndBlocksLiveTranslation(t *testing.T) {
	c := configured()
	c.key = "existing-key"
	c.calls = 9
	c.chars = 321
	c.history = []string{"private"}
	c.frameText = "private"
	c.frameValid = true
	if _, err := c.handle(Request{Version: 1, Method: "forget_key"}); err != nil {
		t.Fatal(err)
	}
	if c.key != "" || c.configured || len(c.history) != 0 || c.frameValid || c.calls != 9 || c.chars != 321 {
		t.Fatal("forget state")
	}
	if _, err := c.translate("hello"); err == nil {
		t.Fatal("unconfigured translation allowed")
	}
}

func TestObserveInputBoundResetsStability(t *testing.T) {
	c := configured()
	c.observe("hello", false)
	if _, err := c.handle(Request{Version: 1, Method: "observe", Text: strings.Repeat("猫", 2001)}); err == nil {
		t.Fatal("oversized observation accepted")
	}
	if c.observed != "" || c.emitted != "" || c.calls != 0 {
		t.Fatal("observation not cleared")
	}
}

func TestOCRSingleFrameCacheScopeExpiryAndClear(t *testing.T) {
	c := configured()
	now := time.Unix(100, 0)
	c.now = func() time.Time { return now }
	invocations := 0
	c.recognizeImage = func(image, path string) (string, error) { invocations++; return "猫", nil }
	if _, cached, err := c.ocr("frame", "engine", "roi-a"); err != nil || cached {
		t.Fatal("first OCR")
	}
	if _, cached, err := c.ocr("frame", "engine", "roi-a"); err != nil || !cached || invocations != 1 {
		t.Fatal("cache missed")
	}
	if _, cached, _ := c.ocr("frame", "engine", "roi-b"); cached || invocations != 2 {
		t.Fatal("scope reused")
	}
	now = now.Add(frameCacheTTL)
	if _, cached, _ := c.ocr("frame", "engine", "roi-b"); cached || invocations != 3 {
		t.Fatal("expired cache reused")
	}
	c.clear()
	if _, cached, _ := c.ocr("frame", "engine", "roi-b"); cached || invocations != 4 {
		t.Fatal("clear did not invalidate")
	}
	c.handle(Request{Version: 1, Method: "observe", Reset: true})
	if _, cached, _ := c.ocr("frame", "engine", "roi-b"); cached || invocations != 5 {
		t.Fatal("reset did not invalidate")
	}
	c.recognizeImage = func(image, path string) (string, error) { return "", errors.New("failed") }
	if _, _, err := c.ocr("new-frame", "engine", "roi-b"); err == nil || c.frameValid {
		t.Fatal("failure cache retained")
	}
}

func TestOCRResultAndScopeBounds(t *testing.T) {
	c := configured()
	called := false
	c.recognizeImage = func(image, path string) (string, error) { called = true; return strings.Repeat("x", maxOCRText+1), nil }
	if _, _, err := c.ocr("frame", "engine", strings.Repeat("x", 129)); err == nil || called {
		t.Fatal("scope bound")
	}
	if _, _, err := c.ocr("frame", "engine", "roi"); err == nil || c.frameValid {
		t.Fatal("result bound")
	}
}

func TestCharacterBudgetBoundaryAndCacheCost(t *testing.T) {
	c := configured()
	c.chars = 9999
	if _, err := c.translate("猫"); err != nil {
		t.Fatal(err)
	}
	if c.chars != 10000 || c.calls != 1 {
		t.Fatal("exact character reservation")
	}
	c.last = time.Time{}
	if _, err := c.translate("犬"); err == nil || c.chars != 10000 || c.calls != 1 {
		t.Fatal("character limit exceeded")
	}
}

func TestStatusRetryDeadline(t *testing.T) {
	c := configured()
	now := time.Unix(100, 0)
	c.now = func() time.Time { return now }
	read := func() map[string]any {
		r, e := c.handle(Request{Version: 1, Method: "status"})
		if e != nil {
			t.Fatal(e)
		}
		return r.(map[string]any)
	}
	if read()["retry_after_ms"] != int64(0) {
		t.Fatal("initial throttle")
	}
	c.translate("猫")
	if read()["retry_after_ms"] != int64(3000) {
		t.Fatal("initial deadline")
	}
	now = now.Add(2999500 * time.Microsecond)
	if read()["retry_after_ms"] != int64(1) {
		t.Fatal("sub-millisecond should round up")
	}
	now = now.Add(time.Second)
	if read()["retry_after_ms"] != int64(0) {
		t.Fatal("negative wait")
	}
}

func TestRequestIDsBounded(t *testing.T) {
	for _, id := range []string{"null", "0", "-1", "1.2", "true", "{}", "[]", `""`, strings.Repeat("1", 257)} {
		if validID(json.RawMessage(id)) {
			t.Fatal("accepted invalid ID", id)
		}
	}
	for _, id := range []string{"1", "9007199254740991", `"request-1"`} {
		if !validID(json.RawMessage(id)) {
			t.Fatal("valid ID rejected", id)
		}
	}
	var out bytes.Buffer
	if err := serve(strings.NewReader(`{"id":{},"version":1,"method":"configure","demo":true}`+"\n"), &out, NewCore()); err != nil {
		t.Fatal(err)
	}
	var reply Response
	if json.Unmarshal(out.Bytes(), &reply) != nil || reply.OK || len(reply.ID) != 0 {
		t.Fatal("invalid ID echo", out.String())
	}
}

func TestNetworkResponseSizeBound(t *testing.T) {
	c := configured()
	c.demo = false
	c.key = "test"
	c.client = &http.Client{Transport: transportFunc(func(*http.Request) (*http.Response, error) {
		return &http.Response{StatusCode: 200, Body: io.NopCloser(strings.NewReader(strings.Repeat("x", 65537)))}, nil
	})}
	if _, err := c.translate("猫"); err == nil || c.calls != 1 {
		t.Fatal("oversized HTTP response accepted/refunded")
	}
}

// A real child-process fixture validates stdin/stdout and environment plumbing on
// Linux and Windows without requiring Tesseract or calling any external service.
func init() {
	if os.Getenv("KOTOBA_CORE_TEST_OCR_CHILD") != "1" {
		return
	}
	if len(os.Args) != 7 || os.Args[1] != "stdin" || os.Args[2] != "stdout" || os.Getenv("OMP_THREAD_LIMIT") != "1" {
		os.Exit(3)
	}
	if _, err := png.Decode(os.Stdin); err != nil {
		os.Exit(4)
	}
	fmt.Fprint(os.Stdout, "猫\n")
	os.Exit(0)
}

func TestOCRChildProcessPipes(t *testing.T) {
	t.Setenv("KOTOBA_CORE_TEST_OCR_CHILD", "1")
	t.Setenv("OMP_THREAD_LIMIT", "8")
	var data bytes.Buffer
	if err := png.Encode(&data, image.NewGray(image.Rect(0, 0, 20, 20))); err != nil {
		t.Fatal(err)
	}
	executable, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	text, err := recognize(base64.StdEncoding.EncodeToString(data.Bytes()), executable)
	if err != nil || text != "猫\n" {
		t.Fatal("child OCR pipes", text, err)
	}
}
