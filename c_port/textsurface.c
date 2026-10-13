#include <SDL2/SDL_ttf.h>
#include "textsurface.h"
#include "surfaces.h"

void TextSurface_render(Surface *self, SDL_Renderer *renderer) {
    TextSurface *data = self->data;
    SDL_Surface *cpu_rendered_text = TTF_RenderUTF8_Blended(Surface_getApp(self)->font, data->text, *data->color);
    SDL_Texture *rendered_text = SDL_CreateTextureFromSurface(renderer, cpu_rendered_text);
    float width = (float)cpu_rendered_text->w / self->rect.w;
    float height = (float)cpu_rendered_text->h / self->rect.h;
    float scale_factor = height<width ? height : width;
    float scaled_width = cpu_rendered_text->w * scale_factor;
    float scaled_height = cpu_rendered_text->h * scale_factor; 
    SDL_FreeSurface(cpu_rendered_text);
    SDL_RenderCopy(renderer, rendered_text, NULL, &(SDL_Rect){self->rect.w/2-scaled_width/2, self->rect.h/2-scaled_height/2, scaled_width, scaled_height});
    SDL_DestroyTexture(rendered_text);
}

SurfaceClass TextSurfaceClass = {.render=TextSurface_render};

Surface* TextSurface_create(Surface* parent, char *text, SDL_Color *color) {
    Surface *self = Surface_create(&TextSurfaceClass, parent, NULL);
    TextSurface *data = calloc(1, sizeof *data);
    data->text = text;
    data->color = color;
    self->data = data;
    return self;
}