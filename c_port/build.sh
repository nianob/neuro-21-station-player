#!/bin/bash

if [[ "$1" == "dev" ]] then
    clang -Wall -Wextra -Werror=implicit-function-declaration -O0 -g -fsanitize=address,undefined -fno-omit-frame-pointer $(pkg-config --cflags --libs sdl2) -o dist/player c_port/*.c && ./dist/player
else
    clang -Wall -Wextra -O3 -DNDEBUG $(pkg-config --cflags --libs sdl2) -o dist/player c_port/*.c
fi