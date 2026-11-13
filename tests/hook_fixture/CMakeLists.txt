cmake_minimum_required(VERSION 3.20)
project(KotobaHookFixture LANGUAGES CXX)
add_executable(KotobaHookFixture main.cpp)
target_link_libraries(KotobaHookFixture user32 gdi32)
