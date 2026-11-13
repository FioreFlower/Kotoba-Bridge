// MIT. Deliberately unprotected, synthetic GDI test window. No files/network/game data.
#include <windows.h>
int main() {
  HWND w=CreateWindowW(L"STATIC",L"Kotoba synthetic hook fixture",WS_OVERLAPPEDWINDOW|WS_VISIBLE,40,40,500,150,nullptr,nullptr,GetModuleHandleW(nullptr),nullptr);
  if(!w)return 2;
  for(int i=0;i<60;i++) {
    MSG m;while(PeekMessageW(&m,nullptr,0,0,PM_REMOVE)){TranslateMessage(&m);DispatchMessageW(&m);}
    HDC dc=GetDC(w);
    // Escaped source avoids compiler locale dependence. Fixed synthetic text only.
    const wchar_t* s=L"\x660E\x65E5\x3001\x307E\x305F\x3053\x3053\x3067\x4F1A\x304A\x3046\x3002";
    const wchar_t* other=L"\x660E\x65E5\x3001\x3053\x3053\x3067\x5F85\x3064\x3002";
    if(i%2)s=other;
    TextOutW(dc,10,45,s,lstrlenW(s));ReleaseDC(w,dc);Sleep(1200);
  }
  DestroyWindow(w);return 0;
}
