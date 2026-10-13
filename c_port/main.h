#pragma once
#include <SDL2/SDL.h>
#include <SDL2/SDL_ttf.h>

typedef struct App {
    char show_hitboxes;
    SDL_Color text_color;
    SDL_Color button_text_color;
    TTF_Font *font;
} App;