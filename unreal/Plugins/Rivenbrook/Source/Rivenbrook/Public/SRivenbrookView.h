// The whole game in one widget.
//
// Both other runtimes draw everything through a single pass - Main._draw() in
// Godot, frame() in the browser - so the Unreal build is one Slate widget with
// an OnPaint that does the same thing, rather than a scene full of actors. The
// view scales to the widget it is given exactly the way the other two scale to
// their window: whole pixels only, and the extra room becomes more world.
#pragma once

#include "CoreMinimal.h"
#include "RivenbrookArt.h"
#include "Widgets/SCompoundWidget.h"

class SRivenbrookView : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SRivenbrookView) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry,
		const FSlateRect& MyCullingRect, FSlateWindowElementList& OutDrawElements,
		int32 LayerId, const FWidgetStyle& InWidgetStyle,
		bool bParentEnabled) const override;

	virtual void Tick(const FGeometry& AllottedGeometry, const double InCurrentTime,
		const float InDeltaTime) override;

	virtual bool SupportsKeyboardFocus() const override { return true; }

private:
	/** Mutable because OnPaint is const and the view has to settle to the
	 *  geometry it is actually given. */
	mutable FRivenbrookArt Art;
	FString LoadError;
	float Time = 0.0f;

	/** Where the cooked assets live, next to the other two runtimes' copies. */
	static FString DataDir();
};
