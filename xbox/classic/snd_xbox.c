#include <math.h>
#include <string.h>
#include <SDL.h>

#include "quakedef.h"
#include "snd_main.h"

static unsigned int xboxaudiotime;

static void Xbox_AudioCallback(void *userdata, Uint8 *stream, int len)
{
	unsigned int factor, requested, available, frames;
	unsigned int start, end;
	(void)userdata;

	if (!snd_renderbuffer)
	{
		memset(stream, 0, (size_t)len);
		return;
	}
	factor = snd_renderbuffer->format.channels * snd_renderbuffer->format.width;
	if (!factor || (unsigned int)len % factor)
	{
		memset(stream, 0, (size_t)len);
		return;
	}
	requested = (unsigned int)len / factor;
	if (SndSys_LockRenderBuffer())
	{
		if (snd_usethreadedmixing)
		{
			S_MixToBuffer(stream, requested);
			if (snd_blocked)
				memset(stream, snd_renderbuffer->format.width == 1 ? 0x80 : 0, (size_t)len);
			SndSys_UnlockRenderBuffer();
			xboxaudiotime += requested;
			return;
		}

		available = snd_renderbuffer->endframe - snd_renderbuffer->startframe;
		frames = available > requested ? requested : available;
		start = snd_renderbuffer->startframe % snd_renderbuffer->maxframes;
		end = (snd_renderbuffer->startframe + frames) % snd_renderbuffer->maxframes;
		if (start > end)
		{
			unsigned int first = (snd_renderbuffer->maxframes - start) * factor;
			unsigned int second = frames * factor - first;
			memcpy(stream, &snd_renderbuffer->ring[start * factor], first);
			memcpy(stream + first, snd_renderbuffer->ring, second);
		}
		else if (frames)
			memcpy(stream, &snd_renderbuffer->ring[start * factor], frames * factor);
		if (frames < requested)
			memset(stream + frames * factor,
				snd_renderbuffer->format.width == 1 ? 0x80 : 0,
				(requested - frames) * factor);
		snd_renderbuffer->startframe += frames;
		SndSys_UnlockRenderBuffer();
	}
	xboxaudiotime += requested;
}

qboolean SndSys_Init(const snd_format_t *requested, snd_format_t *suggested)
{
	SDL_AudioSpec want, got;
	unsigned int buffersize;

	snd_threaded = false;
	if (SDL_InitSubSystem(SDL_INIT_AUDIO) < 0)
	{
		Con_Printf("Xbox audio init failed: %s\n", SDL_GetError());
		return false;
	}

	memset(&want, 0, sizeof(want));
	memset(&got, 0, sizeof(got));
	buffersize = (unsigned int)ceil((double)requested->speed / 25.0);
	want.callback = Xbox_AudioCallback;
	want.userdata = NULL;
	want.freq = requested->speed;
	want.format = requested->width == 1 ? AUDIO_U8 : AUDIO_S16SYS;
	want.channels = (Uint8)requested->channels;
	want.samples = (Uint16)CeilPowerOf2(buffersize);

	if (SDL_OpenAudio(&want, &got) < 0)
	{
		Con_Printf("Xbox audio open failed: %s\n", SDL_GetError());
		SDL_QuitSubSystem(SDL_INIT_AUDIO);
		return false;
	}

	if (want.freq != got.freq || want.format != got.format || want.channels != got.channels)
	{
		if (suggested)
		{
			suggested->speed = got.freq;
			suggested->width = got.format == AUDIO_U8 ? 1 : 2;
			suggested->channels = got.channels;
		}
		SDL_CloseAudio();
		return false;
	}

	snd_threaded = true;
	snd_renderbuffer = Snd_CreateRingBuffer(requested, 0, NULL);
	if (snd_channellayout.integer == SND_CHANNELLAYOUT_AUTO)
		Cvar_SetValueQuick(&snd_channellayout, SND_CHANNELLAYOUT_STANDARD);
	xboxaudiotime = 0;
	SDL_PauseAudio(0);
	Con_Printf("Xbox audio: %d Hz, %d channel(s), %d-bit\n",
		got.freq, got.channels, requested->width * 8);
	return true;
}

void SndSys_Shutdown(void)
{
	SDL_CloseAudio();
	if (snd_renderbuffer)
	{
		Mem_Free(snd_renderbuffer->ring);
		Mem_Free(snd_renderbuffer);
		snd_renderbuffer = NULL;
	}
	SDL_QuitSubSystem(SDL_INIT_AUDIO);
}

void SndSys_Submit(void)
{
}

unsigned int SndSys_GetSoundTime(void)
{
	return xboxaudiotime;
}

qboolean SndSys_LockRenderBuffer(void)
{
	SDL_LockAudio();
	return true;
}

void SndSys_UnlockRenderBuffer(void)
{
	SDL_UnlockAudio();
}

void SndSys_SendKeyEvents(void)
{
}
