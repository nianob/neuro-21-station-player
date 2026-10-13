#pragma once
#include <SDL2/SDL.h>
#include "main.h"

typedef struct Surface Surfce;

typedef struct {
    void (*render)(struct Surface *self, SDL_Renderer *r);
    // The function running when the object is clicked. Returns 1 if click should propagate
    char (*Surface_onClick)(struct Surface *self, int x, int y);
    void (*Surface_onResize)(struct Surface *self);
    SDL_Rect (*getRect)(struct Surface *self);
    SDL_Cursor *cursor;
    App *app;
    char cached;
} SurfaceClass;

typedef struct Surface {
    const SurfaceClass *cls;
    SDL_Rect rect;
    SDL_Texture *texture;
    struct Surface *parent;
    struct Surface *children[8];
    int childCount;
    char redraw;
} Surface;