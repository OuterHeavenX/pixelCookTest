#include "SRivenbrookView.h"

#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"

FString SRivenbrookView::DataDir()
{
	// Where tools/unrealcook.py stages them: plain files under the project's
	// Content directory, read off disk rather than imported. Importing would
	// make a fourth copy of the atlas that can drift from the other three.
	return FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Rivenbrook"));
}

void SRivenbrookView::Construct(const FArguments& InArgs)
{
	FString Error;
	if (!Art.Load(DataDir(), Error))
	{
		LoadError = Error;
		UE_LOG(LogTemp, Error, TEXT("Rivenbrook: %s"), *Error);
	}
	else
	{
		UE_LOG(LogTemp, Display, TEXT("Rivenbrook: %d sprites, %d glyphs from %s"),
			Art.NumFrames(), Art.NumGlyphs(), *DataDir());
	}
	SetCanTick(true);
}

void SRivenbrookView::Tick(const FGeometry& AllottedGeometry, const double InCurrentTime,
	const float InDeltaTime)
{
	Time += InDeltaTime;
}

int32 SRivenbrookView::OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry,
	const FSlateRect& MyCullingRect, FSlateWindowElementList& OutDrawElements,
	int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	const FVector2f Room = FVector2f(AllottedGeometry.GetLocalSize());
	if (Room.X < 1.0f || Room.Y < 1.0f)
	{
		return LayerId;
	}

	// Whole pixels per game pixel, and the leftover room becomes a bigger view
	// rather than bars - the same arithmetic as Art.gd's fit() and fitCanvas().
	Art.Fit(FMath::FloorToInt(Room.X), FMath::FloorToInt(Room.Y));
	const int32 Scale = FMath::Max(1, FMath::Min(
		FMath::FloorToInt(Room.X) / Art.VW, FMath::FloorToInt(Room.Y) / Art.VH));

	// One transform for the whole game, so everything below draws in game
	// pixels and knows nothing about the window it landed in.
	const FGeometry Screen = AllottedGeometry.MakeChild(
		FVector2f(Art.VW, Art.VH),
		FSlateLayoutTransform(float(Scale),
			FVector2f(FMath::RoundToFloat((Room.X - Art.VW * Scale) / 2.0f),
				FMath::RoundToFloat((Room.Y - Art.VH * Scale) / 2.0f))));

	int32 Layer = LayerId;
	Art.Rect(OutDrawElements, Layer++, Screen, FVector2f::ZeroVector,
		FVector2f(Art.VW, Art.VH), FLinearColor(0.039f, 0.031f, 0.071f));

	if (!Art.IsLoaded())
	{
		Art.Text(OutDrawElements, Layer++, Screen,
			TEXT("ASSETS NOT COOKED"), FVector2f(Art.VW / 2.0f, Art.VH / 2.0f - 12),
			FLinearColor(1.0f, 0.42f, 0.42f), TEXT("center"));
		Art.Text(OutDrawElements, Layer++, Screen,
			LoadError.Left(46), FVector2f(Art.VW / 2.0f, Art.VH / 2.0f),
			FLinearColor(0.56f, 0.59f, 0.75f), TEXT("center"));
		Art.Text(OutDrawElements, Layer++, Screen,
			TEXT("run: python tools/unrealcook.py"),
			FVector2f(Art.VW / 2.0f, Art.VH / 2.0f + 14),
			FLinearColor(0.56f, 0.59f, 0.75f), TEXT("center"));
		return Layer;
	}

	// Stage 0. Everything above this line is the runtime; everything below is
	// a standing test of it - one backdrop, one sprite of every kind the game
	// draws, and a line of text - so that a build either shows the game's own
	// art in its own colours or says which part is missing.
	Art.Spr(OutDrawElements, Layer++, Screen, TEXT("bg_dusk"),
		FVector2f((Art.VW - 512) / 2.0f, Art.VH - 64 - 116));

	const TCHAR* Cast[] = { TEXT("aldric_down0"), TEXT("lyra_down0"), TEXT("mira_down0"),
		TEXT("bram_down0"), TEXT("sera_down0") };
	for (int32 i = 0; i < UE_ARRAY_COUNT(Cast); ++i)
	{
		Art.SprFoot(OutDrawElements, Layer, Screen, Cast[i],
			FVector2f(40 + i * 26, Art.VH - 74));
	}
	++Layer;

	const TCHAR* Foes[] = { TEXT("e_slime"), TEXT("e_wolf"), TEXT("e_wight"),
		TEXT("e_ogre"), TEXT("e_warden") };
	float X = Art.VW - 40.0f;
	for (int32 i = UE_ARRAY_COUNT(Foes) - 1; i >= 0; --i)
	{
		const FIntPoint Size = Art.FrameSize(Foes[i]);
		X -= Size.X + 6;
		Art.SprFoot(OutDrawElements, Layer, Screen, Foes[i],
			FVector2f(X + Size.X / 2.0f, Art.VH - 74));
	}
	++Layer;

	Art.Rect(OutDrawElements, Layer++, Screen, FVector2f(0, Art.VH - 64),
		FVector2f(Art.VW, 64), FLinearColor(0.043f, 0.039f, 0.086f));
	Art.Text(OutDrawElements, Layer++, Screen, TEXT("RIVENBROOK"),
		FVector2f(Art.VW / 2.0f, Art.VH - 52), FLinearColor(0.965f, 0.886f, 0.659f),
		TEXT("center"));
	Art.Text(OutDrawElements, Layer++, Screen,
		FString::Printf(TEXT("%d sprites   %d glyphs   view %dx%d at %dx"),
			Art.NumFrames(), Art.NumGlyphs(), Art.VW, Art.VH, Scale),
		FVector2f(Art.VW / 2.0f, Art.VH - 36), FLinearColor(0.56f, 0.59f, 0.75f),
		TEXT("center"));
	Art.Text(OutDrawElements, Layer++, Screen,
		TEXT("stage 0: the art layer draws"),
		FVector2f(Art.VW / 2.0f, Art.VH - 20), FLinearColor(0.56f, 0.75f, 0.63f),
		TEXT("center"));
	return Layer;
}
