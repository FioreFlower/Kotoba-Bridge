package main

import (
	"bufio"
	"bytes"
	"context"
	"crypto/sha256"
	"crypto/tls"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"image/png"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
	"unicode/utf8"
)

const protocol = 1
const maxLine = 12 * 1024 * 1024
const maxResponse = 128 * 1024
const maxOCRText = 16 * 1024
const frameCacheTTL = 3 * time.Second

type Request struct {
	ID         json.RawMessage `json:"id"`
	Version    int             `json:"version"`
	Method     string          `json:"method"`
	Key        string          `json:"key"`
	Pro        bool            `json:"pro"`
	Demo       bool            `json:"demo"`
	Text       string          `json:"text"`
	Reset      bool            `json:"reset"`
	Image      string          `json:"image"`
	Tesseract  string          `json:"tesseract"`
	Scope      string          `json:"scope"`
	Provider   string          `json:"provider"`
	LocalPort  int             `json:"local_port"`
	LocalModel string          `json:"local_model"`
	LocalToken string          `json:"local_token"`
}
type Response struct {
	ID      json.RawMessage `json:"id,omitempty"`
	Version int             `json:"version"`
	OK      bool            `json:"ok"`
	Result  any             `json:"result,omitempty"`
	Error   string          `json:"error,omitempty"`
}
type Core struct {
	key               string
	provider          string
	localPort         int
	localModel        string
	localToken        string
	localHTTP         *http.Client
	pro, demo         bool
	configured        bool
	calls, chars      int
	last              time.Time
	history           []string
	cache             map[string]string
	order             []string
	observed, emitted string
	since             time.Time
	client            *http.Client
	now               func() time.Time
	recognizeImage    func(string, string) (string, error)
	frameKey          [32]byte
	frameText         string
	frameAt           time.Time
	frameValid        bool
}

func NewCore() *Core {
	tr := &http.Transport{Proxy: nil, TLSClientConfig: &tls.Config{MinVersion: tls.VersionTLS12}, TLSHandshakeTimeout: 10 * time.Second, ResponseHeaderTimeout: 15 * time.Second}
	client := &http.Client{Transport: tr, Timeout: 15 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return errors.New("redirect blocked") }}
	return &Core{demo: true, localHTTP: localClient(), client: client, cache: map[string]string{}, now: time.Now, recognizeImage: recognize}
}
func normalize(s string) string { return strings.Join(strings.Fields(s), " ") }
func (c *Core) clear() {
	c.history = nil
	c.cache = map[string]string{}
	c.order = nil
	c.observed = ""
	c.emitted = ""
	c.since = time.Time{}
	c.clearFrame()
}
func (c *Core) clearFrame() {
	c.frameKey = [32]byte{}
	c.frameText = ""
	c.frameAt = time.Time{}
	c.frameValid = false
}

// Cache only a successful result, never image bytes. Scope separates ROI sessions.
// A short TTL also bounds stale results after model/executable changes on disk.
func (c *Core) ocr(encoded, path, scope string) (string, bool, error) {
	if len(scope) > 128 || len(encoded) > 11*1024*1024 || len(path) > 4096 {
		return "", false, errors.New("OCR 요청 크기 한도를 초과했습니다.")
	}
	digest := sha256.Sum256([]byte(path + "\x00" + scope + "\x00" + encoded))
	now := c.now()
	if c.frameValid && digest == c.frameKey && now.Sub(c.frameAt) >= 0 && now.Sub(c.frameAt) < frameCacheTTL {
		return c.frameText, true, nil
	}
	text, err := c.recognizeImage(encoded, path)
	if err != nil {
		c.clearFrame()
		return "", false, err
	}
	if len(text) > maxOCRText || !utf8.ValidString(text) {
		c.clearFrame()
		return "", false, errors.New("OCR 응답 크기 또는 인코딩 오류")
	}
	c.frameKey, c.frameText, c.frameAt, c.frameValid = digest, text, now, true
	return text, false, nil
}

func validKey(key string) bool {
	if len(key) > 4096 || strings.TrimSpace(key) == "" {
		return false
	}
	for _, ch := range key {
		if ch <= 32 || ch >= 127 {
			return false
		}
	}
	return true
}

func (c *Core) observe(text string, reset bool) string {
	if reset {
		c.observed = ""
		c.emitted = ""
		c.since = time.Time{}
	}
	text = normalize(text)
	now := c.now()
	if text != c.observed {
		c.observed = text
		c.since = now
	}
	if text == "" {
		c.emitted = ""
		return ""
	}
	if text != c.emitted && now.Sub(c.since) >= 900*time.Millisecond {
		c.emitted = text
		return text
	}
	return ""
}
func (c *Core) translate(text string) (string, error) {
	if !c.configured {
		return "", errors.New("먼저 코어를 설정하세요.")
	}
	text = normalize(text)
	n := utf8.RuneCountInString(text)
	if n == 0 || n > 2000 {
		return "", errors.New("번역 원문은 1~2,000자여야 합니다.")
	}
	ctxRunes := []rune(strings.Join(c.history, "\n"))
	if len(ctxRunes) > 1500 {
		ctxRunes = ctxRunes[len(ctxRunes)-1500:]
	}
	ctxText := string(ctxRunes)
	key := text + "\x00" + ctxText
	if cached, ok := c.cache[key]; ok {
		return cached, nil
	}
	now := c.now()
	if c.provider != "local" && !c.last.IsZero() && now.Sub(c.last) < 3*time.Second {
		return "", errors.New("최소 호출 간격 3초: 잠시 후 재개하세요.")
	}
	if c.calls >= 100 || c.chars+n > 10000 {
		return "", errors.New("세션 사용 한도에 도달했습니다.")
	}
	c.calls++
	c.chars += n
	c.last = now
	var result string
	if c.demo {
		samples := map[string]string{"こんにちは。": "안녕하세요.", "一緒に帰りましょう。": "같이 돌아가요.", "明日、またここで会おう。": "내일 여기서 다시 만나자."}
		result = samples[text]
		if result == "" {
			result = "[데모: 실제 번역 아님] " + text
		}
	} else {
		var err error
		if c.provider == "local" {
			result, err = c.requestLocal(text, ctxText)
		} else {
			result, err = c.requestTranslation(text, ctxText)
		}
		if err != nil {
			return "", err
		}
	}
	c.cache[key] = result
	c.order = append(c.order, key)
	if len(c.order) > 128 {
		delete(c.cache, c.order[0])
		c.order = c.order[1:]
	}
	c.history = append(c.history, text)
	if len(c.history) > 3 {
		c.history = c.history[len(c.history)-3:]
	}
	return result, nil
}
func (c *Core) requestTranslation(text, ctxText string) (string, error) {
	endpoint := "https://api-free.deepl.com/v2/translate"
	if c.pro {
		endpoint = "https://api.deepl.com/v2/translate"
	}
	payload, _ := json.Marshal(map[string]any{"text": []string{text}, "source_lang": "JA", "target_lang": "KO", "context": ctxText, "split_sentences": "nonewlines"})
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(payload))
	if err != nil {
		return "", errors.New("번역 요청 생성 실패")
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "DeepL-Auth-Key "+c.key)
	resp, err := c.client.Do(req)
	if err != nil {
		return "", errors.New("네트워크 또는 인증서 오류. 과금 여부가 불확실하여 재시도하지 않습니다.")
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		switch resp.StatusCode {
		case 403:
			return "", errors.New("API 키 인증 실패. 자동 재시도하지 않습니다.")
		case 429:
			return "", errors.New("서버 호출 제한. 자동 재시도하지 않습니다.")
		case 456:
			return "", errors.New("DeepL 사용량 한도 초과. 자동 재시도하지 않습니다.")
		}
		return "", errors.New("번역 서버 오류. 자동 재시도하지 않습니다.")
	}
	data, err := io.ReadAll(io.LimitReader(resp.Body, 65537))
	if err != nil || len(data) > 65536 {
		return "", errors.New("번역 응답 크기 또는 읽기 오류")
	}
	var body struct {
		Translations []struct {
			Text string `json:"text"`
		} `json:"translations"`
	}
	if json.Unmarshal(data, &body) != nil || len(body.Translations) != 1 || strings.TrimSpace(body.Translations[0].Text) == "" || utf8.RuneCountInString(body.Translations[0].Text) > 20000 {
		return "", errors.New("잘못된 번역 응답")
	}
	return body.Translations[0].Text, nil
}
func recognize(encoded, path string) (string, error) {
	if len(encoded) > 11*1024*1024 {
		return "", errors.New("OCR 이미지가 너무 큽니다.")
	}
	data, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		return "", errors.New("잘못된 이미지 인코딩")
	}
	config, err := png.DecodeConfig(bytes.NewReader(data))
	if err != nil || config.Width < 1 || config.Height < 1 || config.Width > 4096 || config.Height > 4096 || config.Width*config.Height > 2100000 {
		return "", errors.New("OCR PNG 크기/형식 오류")
	}
	if path == "" {
		path = "tesseract"
	}
	ctx, cancel := context.WithTimeout(context.Background(), 6*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, path, "stdin", "stdout", "-l", "jpn", "--psm", "6")
	// Bound Wait even if an engine descendant keeps inherited pipes open after exit.
	cmd.WaitDelay = 500 * time.Millisecond
	configureChild(cmd)
	cmd.Stdin = bytes.NewReader(data)
	cmd.Stderr = io.Discard
	tessdata := ""
	if filepath.IsAbs(path) {
		sibling := filepath.Join(filepath.Dir(path), "tessdata")
		if info, e := os.Stat(filepath.Join(sibling, "jpn.traineddata")); e == nil && !info.IsDir() {
			tessdata = sibling
		}
	}
	for _, e := range os.Environ() {
		if !strings.HasPrefix(strings.ToUpper(e), "OMP_THREAD_LIMIT=") && !(tessdata != "" && strings.HasPrefix(strings.ToUpper(e), "TESSDATA_PREFIX=")) {
			cmd.Env = append(cmd.Env, e)
		}
	}
	cmd.Env = append(cmd.Env, "OMP_THREAD_LIMIT=1")
	if tessdata != "" {
		cmd.Env = append(cmd.Env, "TESSDATA_PREFIX="+tessdata)
	}
	// Bound child output even if an unexpected executable is configured.
	out := &limitedBuffer{remaining: maxOCRText}
	cmd.Stdout = out
	if err = cmd.Run(); err != nil || out.overflow {
		return "", errors.New("OCR 실패: 엔진 경로·jpn 모델·시간 초과를 확인하세요.")
	}
	text := out.buf.String()
	if !utf8.ValidString(text) {
		return "", errors.New("OCR 응답 인코딩 오류")
	}
	return text, nil
}

type limitedBuffer struct {
	buf       bytes.Buffer
	remaining int
	overflow  bool
}

func (b *limitedBuffer) Write(p []byte) (int, error) {
	n := len(p)
	if n > b.remaining {
		b.overflow = true
		p = p[:b.remaining]
	}
	b.buf.Write(p)
	b.remaining -= len(p)
	return n, nil
}
func (c *Core) handle(r Request) (any, error) {
	if r.Version != protocol {
		return nil, errors.New("코어/UI 프로토콜 버전이 다릅니다.")
	}
	switch r.Method {
	case "hello":
		return map[string]any{"protocol": protocol, "name": "KotobaBridgeCore", "version": "0.4.0-dev"}, nil
	case "configure":
		provider := r.Provider
		if provider == "" {
			provider = "deepl"
		}
		if provider != "deepl" && provider != "local" {
			return nil, errors.New("지원하지 않는 번역 제공자")
		}
		if !r.Demo && provider == "local" {
			if r.Key != "" || !validLocal(r.LocalPort, r.LocalModel) || !validLocalToken(r.LocalToken) {
				return nil, errors.New("로컬 설정 오류: 포트 1024~65535와 모델 별칭을 확인하세요. API 키는 보내지 마세요.")
			}
			c.key = ""
			c.provider = "local"
			c.localPort = r.LocalPort
			c.localModel = r.LocalModel
			c.localToken = r.LocalToken
			c.demo = false
			c.configured = true
			c.clear()
			return map[string]any{"configured": true, "provider": "local"}, nil
		}
		if r.Key != "" && !validKey(r.Key) {
			return nil, errors.New("API 키 형식을 확인하세요. 공백·제어문자는 허용하지 않습니다.")
		}
		if !r.Demo && r.Key == "" && c.key == "" {
			return nil, errors.New("API 키가 필요합니다.")
		}
		if r.Key != "" {
			c.key = strings.TrimSpace(r.Key)
		}
		c.localToken = ""
		c.provider = provider
		c.pro = r.Pro
		c.demo = r.Demo
		c.configured = true
		c.clear()
		return map[string]any{"configured": true}, nil
	case "ocr":
		text, cached, err := c.ocr(r.Image, r.Tesseract, r.Scope)
		return map[string]any{"text": text, "cached": cached}, err
	case "observe":
		if utf8.RuneCountInString(r.Text) > 2000 {
			c.observe("", true)
			return nil, errors.New("인식 텍스트는 2,000자 이하여야 합니다.")
		}
		if r.Reset {
			c.clearFrame()
		}
		return map[string]any{"text": c.observe(r.Text, r.Reset)}, nil
	case "translate":
		text, err := c.translate(r.Text)
		return map[string]any{"text": text, "calls": c.calls, "chars": c.chars}, err
	case "status":
		remaining := 3*time.Second - c.now().Sub(c.last)
		retryAfter := int64(0)
		if c.provider != "local" && !c.last.IsZero() && remaining > 0 {
			retryAfter = int64((remaining + time.Millisecond - 1) / time.Millisecond)
		}
		return map[string]any{"calls": c.calls, "chars": c.chars, "retry_after_ms": retryAfter, "remaining_calls": 100 - c.calls, "remaining_chars": 10000 - c.chars}, nil
	case "clear":
		c.clear()
		return map[string]bool{"cleared": true}, nil
	case "forget_key":
		c.key = ""
		c.configured = false
		c.demo = true
		c.clear()
		return map[string]bool{"forgotten": true}, nil
	case "shutdown":
		return map[string]bool{"shutdown": true}, nil
	default:
		return nil, errors.New("지원하지 않는 코어 명령입니다.")
	}
}
func validID(raw json.RawMessage) bool {
	if len(raw) == 0 || len(raw) > 256 {
		return false
	}
	var number uint64
	if json.Unmarshal(raw, &number) == nil && number > 0 && number <= 9007199254740991 {
		return true
	}
	var value string
	return json.Unmarshal(raw, &value) == nil && len(value) > 0 && len(value) <= 64
}

func serve(in io.Reader, out io.Writer, c *Core) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 64*1024), maxLine)
	writer := bufio.NewWriter(out)
	defer writer.Flush()
	for scanner.Scan() {
		var req Request
		res := Response{Version: protocol}
		if err := json.Unmarshal(scanner.Bytes(), &req); err != nil {
			res.Error = "잘못된 JSON 요청입니다."
		} else if !validID(req.ID) {
			res.Error = "요청 ID는 1 이상 정수 또는 64자 이하 문자열이어야 합니다."
		} else {
			res.ID = req.ID
			result, err := c.handle(req)
			if err != nil {
				res.Error = err.Error()
			} else {
				res.OK = true
				res.Result = result
			}
		}
		data, err := json.Marshal(res)
		if err != nil {
			return errors.New("response encoding failed")
		}
		if len(data) > maxResponse {
			data, _ = json.Marshal(Response{ID: req.ID, Version: protocol, Error: "코어 응답 크기 한도를 초과했습니다."})
		}
		if _, err = writer.Write(append(data, '\n')); err != nil {
			return err
		}
		if err = writer.Flush(); err != nil {
			return err
		}
		if res.OK && req.Method == "shutdown" {
			return nil
		}
	}
	if scanner.Err() != nil {
		return errors.New("input exceeded bounds or closed unexpectedly")
	}
	return nil
}
func main() {
	if err := serve(os.Stdin, os.Stdout, NewCore()); err != nil {
		fmt.Fprintln(os.Stderr, "코어 통신이 종료되었습니다.")
		os.Exit(1)
	}
}
