#include "main.h"
#include "surfaces.h"

int SURFACE_MAX_CHILDS = 8;

SDL_Renderer *renderer;

void Surface_setup() {
    SDL_Window *window = SDL_CreateWindow("Dummy Title", 0, 0, 500, 500, 0);
    renderer = SDL_CreateRenderer(window, 0, 0);
}

App* Surface_getApp(Surface *self) {
    if (self->cls->app) {
        return self->cls->app;
    } else if (!self->parent) {
        return NULL;
    }
    return Surface_getApp(self->parent);
}


int Surface_getX(Surface *self) {
    if (self->parent) {
        return Surface_getX(self->parent) + self->rect.x;
    } else {
        return self->rect.x;
    }
}

int Surface_getY(Surface *self) {
    if (self->parent) {
        return Surface_getY(self->parent) + self->rect.y;
    } else {
        return self->rect.y;
    }
}

void Surface_reallocateTexture(Surface *self) {
    if (self->texture) {
        SDL_DestroyTexture(self->texture);
        self->texture = NULL;
    }
    if (self->rect.w <= 0 || self->rect.h <= 0) {
        printf("WARNING: Attempted to set surface size <= 0!\n");
        return;
    };

    self->texture = SDL_CreateTexture(renderer, SDL_PIXELFORMAT_RGBA8888, SDL_TEXTUREACCESS_TARGET, self->rect.w, self->rect.h);
    SDL_SetTextureBlendMode(self->texture, SDL_BLENDMODE_BLEND);
    
    if (self->cls->cached) {
        self->redraw = 1;
    }
}

// Updates the surface and all subsurfaces
void Surface_update(Surface *self) {
    if (self->cls->cached) {
        if (!self->redraw) return;
        self->redraw = 0;
    }

    for (int i=0; i<self->childCount; i++) {
        Surface_update(self->children[i]);
    }

    SDL_SetRenderTarget(renderer, self->texture);
    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 0);
    SDL_RenderClear(renderer);

    if (self->cls->render) {
        self->cls->render(self, renderer);
    }

    for (int i=0; i<self->childCount; i++) {
        SDL_RenderCopy(renderer, self->children[i]->texture, NULL, &self->children[i]->rect);
    }

    App* app = Surface_getApp(self);
    if (app && app->show_hitboxes) {
        SDL_SetRenderDrawColor(renderer, 255, 0, 0, 255);
        SDL_RenderDrawRect(renderer, NULL);
    }
}

/*
Checks if an **absolute** position collides this surface
        
    Args:
        x: the absolute x position
        y: the absolute y position

    Returns:
        bool: Wether or not the mouse collides this surface
*/
char Surface_collide(Surface *self, int x, int y) {
    int moved_x = x - Surface_getX(self);
    int moved_y = y - Surface_getY(self);

    return (
        0 <= moved_x && moved_x < self->rect.w &&
        0 <= moved_y && moved_y < self->rect.w
    );
}

typedef void (*SurfaceFunc)(Surface *target, int x, int y);
/*
Passes a function to a subsurface
        
    Args:
        func: the function to call
        x: the x position
        y: the y position
        ...: all additional arguments are passed on

    Returns:
        tuple:
            success: Wether or not the function has been passed on
            
            return: What the function returned, None if no function was executed
*/
char passFunction(Surface *self, SurfaceFunc func, int x, int y) {
    for (int i = self->childCount - 1; i>=0; i--) {
        Surface *child = self->children[i];
        if (Surface_collide(self, x, y)) {
            func(child, x, y);
            return 1;
        }
    }
    return 0;
}

void Surface_onClick(Surface *self, int x, int y) {
    if (self->cls->onClick) {
        if (!self->cls->onClick(self, x, y)) {
            return;
        }
    }
    passFunction(self, Surface_onClick, x, y);
}

void Surface_setCursor(Surface *self, int x, int y) {
    if (!passFunction(self, Surface_setCursor, x, y)) {
        SDL_SetCursor(self->cls->cursor);
    }
}

void Surface_onResize(Surface *self) {
    Surface_reallocateTexture(self);
    for (int i=0; i<self->childCount; i++) {
        Surface *child = self->children[i];
        if (child->cls->cached) {
            child->redraw = 1;
        }
        if (child->cls->getRect) {
            child->rect = child->cls->getRect(child);
        }
    }

    if (self->cls->onResize) {
        self->cls->onResize(self);
    }
}

void Surface_addChild(Surface *self, Surface *child) {
    if (self->childCount >= SURFACE_MAX_CHILDS) {
        printf("WARNING: Max child count exceeded!\n");
    }
    self->children[self->childCount] = child;
    self->childCount++;

    child->parent = self;
}

void Surface_removeChild(Surface *self, Surface *child) {
    int pos = -1;
    for (int i=0; i<self->childCount; i++) {
        if (self->children[i] == child) {
            pos = i;
            break;
        }
    }
    if (pos == -1) {
        printf("WARNING: Attempted to remove unknown child!\n");
        return;
    }

    self->childCount--;
    for (int i=pos; i<self->childCount; i++) {
        self->children[i] = self->children[i+1];
    }

    child->parent = NULL;
}

Surface* Surface_create(SurfaceClass *cls, Surface* parent, SDL_Rect *rect) {
    Surface *self = calloc(1, sizeof *self);
    self->cls = cls;
    if (parent) {
        Surface_addChild(parent, self);
    }
    if (rect) {
        self->rect = *rect;
    } else {
        self->rect = (SDL_Rect){0, 0, 1, 1};
    }
    Surface_onResize(self);
    return self;
}

void Surface_destroy(Surface *self) {
    if (self->data) {
        free(self->data);
    }
    if (self->parent) {
        Surface_removeChild(self->parent, self);
    }
    SDL_DestroyTexture(self->texture);
    free(self);
}

void Surface_destroyRecursive(Surface *self) {
    while (self->childCount > 0) {
        Surface_destroyRecursive(self->children[0]);
    }
    Surface_destroy(self);
}