// The sprite atlas and the bitmap font, read off disk at startup.
//
// This is the Unreal half of what Art.gd and the top of game.js do: one
// texture page, a frame table, a glyph sheet built from the same 5x7 font the
// other two runtimes use, and the fifteen drawing primitives the whole game is
// made of. Nothing above this layer knows it is running in Unreal.
#pragma once

#include "CoreMinimal.h"
#include "Styling/SlateBrush.h"

class FSlateWindowElementList;
struct FGeometry;

/** One sprite's rectangle on the atlas page, in pixels. */
struct FRivenFrame
{
	int32 X = 0;
	int32 Y = 0;
	int32 W = 0;
	int32 H = 0;
};

class FRivenbrookArt
{
public:
	/** The virtual screen. Kept identical to Art.gd and game.js: never
	 *  smaller than the 320x180 the game was composed in, never wider than a
	 *  backdrop can cover, and always a whole number of real pixels per game
	 *  pixel. */
	static constexpr int32 VMinW = 320;
	static constexpr int32 VMinH = 180;
	static constexpr int32 VMaxW = 512;
	static constexpr int32 VMaxH = 288;
	static constexpr int32 Tile = 16;
	static constexpr int32 GlyphW = 6;
	static constexpr int32 GlyphH = 8;
	static constexpr int32 FontW = 5;
	static constexpr int32 FontRows = 7;

	int32 VW = VMinW;
	int32 VH = VMinH;

	/** Choose the view for a window of this size; true when it changed. */
	bool Fit(int32 WindowW, int32 WindowH);

	/** Load atlas.png, atlas.json and font.json from the content directory.
	 *  Returns false and fills OutError when anything is missing, because a
	 *  half-loaded atlas draws as a screen of nothing and says why never. */
	bool Load(const FString& DataDir, FString& OutError);

	bool IsLoaded() const { return bLoaded; }
	const FString& GetError() const { return LoadError; }
	int32 NumFrames() const { return Frames.Num(); }
	int32 NumGlyphs() const { return Glyphs.Num(); }

	/** A sprite's size in game pixels; zero when the name is unknown. */
	FIntPoint FrameSize(const FString& Name) const;

	/** Draw a sprite with its top-left at Pos. */
	void Spr(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo,
		const FString& Name, const FVector2f& Pos, float Scale = 1.0f,
		const FLinearColor& Tint = FLinearColor::White) const;

	/** Part of a sprite stretched over a rectangle. Carries one pixel of a
	 *  backdrop's sky up over the headroom a tall view has. */
	void SprStretched(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo,
		const FString& Name, const FVector2f& Pos, const FVector2f& Size,
		const FIntRect& Part) const;

	/** Sprites are not all one size - characters are 16x24 and 24x32 - so
	 *  everything anchors on the feet rather than on a top-left offset. */
	void SprFoot(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo,
		const FString& Name, const FVector2f& Foot, float Scale = 1.0f,
		const FLinearColor& Tint = FLinearColor::White) const;

	/** Whole steps only: a sprite at 1.5x lands half its pixels on double
	 *  size and half on single, and the art crawls. */
	float ScaleFor(const FString& Name, float TargetH,
		const TArray<float>& Steps = { 1.0f, 1.5f, 2.0f, 3.0f }) const;

	void Rect(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo,
		const FVector2f& Pos, const FVector2f& Size, const FLinearColor& Color) const;

	int32 TextWidth(const FString& S) const { return S.Len() * GlyphW; }

	/** Text is one white glyph sheet tinted per draw, so a line can be any
	 *  colour without a second copy of the font. */
	void Text(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo,
		const FString& S, const FVector2f& Pos,
		const FLinearColor& Color = FLinearColor(0.957f, 0.957f, 0.925f),
		const FString& Align = TEXT("left"), bool bShadow = true) const;

private:
	bool bLoaded = false;
	FString LoadError;

	TMap<FString, FRivenFrame> Frames;
	TMap<TCHAR, int32> Glyphs;          // character -> column on the sheet

	UTexture2D* AtlasTexture = nullptr;
	UTexture2D* FontTexture = nullptr;
	FIntPoint AtlasSize = FIntPoint::ZeroValue;
	FIntPoint FontSize = FIntPoint::ZeroValue;

	/** One brush per sprite, built once at load. Slate draws a sub-rect of a
	 *  texture through a brush's UV region, and mutating one brush per blit
	 *  fights Slate's own caching. */
	TMap<FString, FSlateBrush> Brushes;
	TArray<FSlateBrush> GlyphBrushes;   // indexed the same as Glyphs' values

	bool LoadPng(const FString& Path, TArray<uint8>& OutPixels,
		FIntPoint& OutSize, FString& OutError) const;
	static UTexture2D* MakeTexture(const TArray<uint8>& Pixels, FIntPoint Size);
	FSlateBrush MakeBrush(UTexture2D* Texture, FIntPoint TexSize,
		const FIntRect& Region) const;
	bool BuildFont(const FString& Path, FString& OutError);
};
