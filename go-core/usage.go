package main

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"time"
)

type AccountUsage struct {
	CharacterCount *int64 `json:"character_count"`
	CharacterLimit *int64 `json:"character_limit"`
	KeyCount       *int64 `json:"api_key_character_count,omitempty"`
	KeyLimit       *int64 `json:"api_key_character_limit,omitempty"`
	CheckedAt      string `json:"checked_at"`
}

func (c *Core) usage() (AccountUsage, error) {
	var out AccountUsage
	if !c.configured || c.demo || c.provider == "local" || c.key == "" {
		return out, errors.New("DeepL 실제 모드와 키가 필요합니다. 데모/로컬에서는 조회하지 않습니다.")
	}
	now := c.now()
	if !c.usageLast.IsZero() && now.Sub(c.usageLast) < time.Minute {
		return out, errors.New("사용량 조회는 최소 60초 간격입니다. 자동 재시도하지 않습니다.")
	}
	c.usageLast = now
	endpoint := "https://api-free.deepl.com/v2/usage"
	if c.pro {
		endpoint = "https://api.deepl.com/v2/usage"
	}
	req, _ := http.NewRequest(http.MethodGet, endpoint, nil)
	req.Header.Set("Authorization", "DeepL-Auth-Key "+c.key)
	resp, err := c.client.Do(req)
	if err != nil {
		return out, errors.New("DeepL 사용량 조회 연결 실패")
	}
	defer resp.Body.Close()
	switch resp.StatusCode {
	case 200:
	case 403:
		return out, errors.New("DeepL 사용량 인증 실패: 키와 Free/Pro 종류를 확인하세요.")
	case 429:
		return out, errors.New("DeepL 사용량 조회 제한. 자동 재시도하지 않습니다.")
	default:
		return out, errors.New("DeepL 사용량 조회 서버 오류")
	}
	data, err := io.ReadAll(io.LimitReader(resp.Body, maxResponse+1))
	if err != nil || len(data) > maxResponse {
		return out, errors.New("DeepL 사용량 응답 크기/읽기 오류")
	}
	if json.Unmarshal(data, &out) != nil || out.CharacterCount == nil {
		return AccountUsage{}, errors.New("DeepL 사용량 응답 형식 오류")
	}
	for _, v := range []*int64{out.CharacterCount, out.CharacterLimit, out.KeyCount, out.KeyLimit} {
		if v != nil && *v < 0 {
			return AccountUsage{}, errors.New("DeepL 사용량 응답 값 오류")
		}
	}
	out.CheckedAt = c.now().UTC().Format(time.RFC3339)
	return out, nil
}
