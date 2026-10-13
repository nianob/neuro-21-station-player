#include "textsurface.h"
#include "surfaces.h"

TextSurface TextSurface_Create(Surface* parent, char* text) {
    
}

void TextSurface_Render(Surface *self, SDL_Renderer *renderer) {
    // SDL_Texture *rendered_text = ;
    
}

SurfaceClass TextSurfaceClass = {.render=TextSurface_Render};