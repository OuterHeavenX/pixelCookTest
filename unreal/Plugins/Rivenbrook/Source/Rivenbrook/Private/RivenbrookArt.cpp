#include "RivenbrookArt.h"

#include "Engine/Texture2D.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "Misc/FileHelper.h"
#include "Modules/ModuleManager.h"
#include "Rendering/DrawElements.h"
#include "Runtime/Launch/Resources/Version.h"
#include "Styling/CoreStyle.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	/** Slate's UV region type moved from FBox2D to FBox2f during UE5. If this
	 *  is the line the compiler stops on, the other branch is the fix. */
	void SetBrushUV(FSlateBrush& Brush, float U0, float V0, float U1, float V1)
	{
#if ENGINE_MAJOR_VERSION >= 5 && ENGINE_MINOR_VERSION >= 1
		Brush.SetUVRegion(FBox2f(FVector2f(U0, V0), FVector2f(U1, V1)));
#else
		Brush.SetUVRegion(FBox2D(FVector2D(U0, V0), FVector2D(U1, V1)));
#endif
	}

	/** The drop shadow every string in the game has, one pixel down and right. */
	const FLinearColor TextShadow = FLinearColor(0.071f, 0.063f, 0.110f);
}

bool FRivenbrookArt::Fit(int32 WindowW, int32 WindowH)
{
	const int32 Scale = FMath::Max(1, FMath::Min(WindowW / VMinW, WindowH / VMinH));
	const int32 W = FMath::Clamp((WindowW / Scale) & ~1, VMinW, VMaxW);
	const int32 H = FMath::Clamp((WindowH / Scale) & ~1, VMinH, VMaxH);
	if (W == VW && H == VH)
	{
		return false;
	}
	VW = W;
	VH = H;
	return true;
}

bool FRivenbrookArt::LoadPng(const FString& Path, TArray<uint8>& OutPixels,
	FIntPoint& OutSize, FString& OutError) const
{
	TArray<uint8> Raw;
	if (!FFileHelper::LoadFileToArray(Raw, *Path))
	{
		OutError = FString::Printf(TEXT("cannot read %s"), *Path);
		return false;
	}
	IImageWrapperModule& Module =
		FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper"));
	const TSharedPtr<IImageWrapper> Wrapper = Module.CreateImageWrapper(EImageFormat::PNG);
	if (!Wrapper.IsValid() || !Wrapper->SetCompressed(Raw.GetData(), Raw.Num()))
	{
		OutError = FString::Printf(TEXT("%s is not a PNG this build can read"), *Path);
		return false;
	}
	if (!Wrapper->GetRaw(ERGBFormat::BGRA, 8, OutPixels))
	{
		OutError = FString::Printf(TEXT("cannot decode %s"), *Path);
		return false;
	}
	OutSize = FIntPoint(Wrapper->GetWidth(), Wrapper->GetHeight());
	return true;
}

UTexture2D* FRivenbrookArt::MakeTexture(const TArray<uint8>& Pixels, FIntPoint Size)
{
	UTexture2D* Texture = UTexture2D::CreateTransient(Size.X, Size.Y, PF_B8G8R8A8);
	if (Texture == nullptr)
	{
		return nullptr;
	}
	// Nearest neighbour, no mips, no compression: this is pixel art and every
	// one of those defaults would smear it.
	Texture->Filter = TextureFilter::TF_Nearest;
	Texture->CompressionSettings = TextureCompressionSettings::TC_VectorDisplacementmap;
	Texture->MipGenSettings = TextureMipGenSettings::TMGS_NoMipmaps;
	Texture->SRGB = true;
	Texture->AddToRoot();   // nothing else holds a reference to it

	FTexture2DMipMap& Mip = Texture->GetPlatformData()->Mips[0];
	void* Data = Mip.BulkData.Lock(LOCK_READ_WRITE);
	FMemory::Memcpy(Data, Pixels.GetData(), Pixels.Num());
	Mip.BulkData.Unlock();
	Texture->UpdateResource();
	return Texture;
}

FSlateBrush FRivenbrookArt::MakeBrush(UTexture2D* Texture, FIntPoint TexSize,
	const FIntRect& Region) const
{
	FSlateBrush Brush;
	Brush.SetResourceObject(Texture);
	Brush.ImageSize = FVector2D(Region.Width(), Region.Height());
	Brush.DrawAs = ESlateBrushDrawType::Image;
	Brush.Tiling = ESlateBrushTileType::NoTile;
	SetBrushUV(Brush,
		float(Region.Min.X) / float(TexSize.X), float(Region.Min.Y) / float(TexSize.Y),
		float(Region.Max.X) / float(TexSize.X), float(Region.Max.Y) / float(TexSize.Y));
	return Brush;
}

bool FRivenbrookArt::BuildFont(const FString& Path, FString& OutError)
{
	// The font arrives as {character: ["01100", ...] x7} - the same table the
	// browser build compiles into itself and the Godot build reads. It is
	// rebuilt here into one white glyph sheet, tinted per draw.
	FString Json;
	if (!FFileHelper::LoadFileToString(Json, *Path))
	{
		OutError = FString::Printf(TEXT("cannot read %s"), *Path);
		return false;
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		OutError = FString::Printf(TEXT("%s is not valid JSON"), *Path);
		return false;
	}

	TArray<FString> Keys;
	Root->Values.GetKeys(Keys);
	Keys.Sort();

	FontSize = FIntPoint(Keys.Num() * GlyphW, GlyphH);
	TArray<uint8> Pixels;
	Pixels.SetNumZeroed(FontSize.X * FontSize.Y * 4);

	int32 Column = 0;
	for (const FString& Key : Keys)
	{
		if (Key.Len() != 1)
		{
			continue;
		}
		const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
		if (!Root->TryGetArrayField(Key, Rows) || Rows->Num() != FontRows)
		{
			OutError = FString::Printf(TEXT("glyph '%s' is not %d rows"), *Key, FontRows);
			return false;
		}
		for (int32 Y = 0; Y < FontRows; ++Y)
		{
			const FString Row = (*Rows)[Y]->AsString();
			for (int32 X = 0; X < FontW && X < Row.Len(); ++X)
			{
				if (Row[X] != TCHAR('1'))
				{
					continue;
				}
				const int32 Index = ((Y * FontSize.X) + Column * GlyphW + X) * 4;
				Pixels[Index + 0] = 255;   // B
				Pixels[Index + 1] = 255;   // G
				Pixels[Index + 2] = 255;   // R
				Pixels[Index + 3] = 255;   // A
			}
		}
		Glyphs.Add(Key[0], Column);
		++Column;
	}

	FontTexture = MakeTexture(Pixels, FontSize);
	if (FontTexture == nullptr)
	{
		OutError = TEXT("cannot create the glyph sheet texture");
		return false;
	}
	GlyphBrushes.SetNum(Column);
	for (int32 i = 0; i < Column; ++i)
	{
		GlyphBrushes[i] = MakeBrush(FontTexture, FontSize,
			FIntRect(i * GlyphW, 0, i * GlyphW + GlyphW, GlyphH));
	}
	return true;
}

bool FRivenbrookArt::Load(const FString& DataDir, FString& OutError)
{
	bLoaded = false;
	LoadError.Reset();
	Frames.Reset();
	Brushes.Reset();
	Glyphs.Reset();
	GlyphBrushes.Reset();

	TArray<uint8> Pixels;
	if (!LoadPng(DataDir / TEXT("atlas.png"), Pixels, AtlasSize, OutError))
	{
		LoadError = OutError;
		return false;
	}
	AtlasTexture = MakeTexture(Pixels, AtlasSize);
	if (AtlasTexture == nullptr)
	{
		OutError = TEXT("cannot create the atlas texture");
		LoadError = OutError;
		return false;
	}

	FString Json;
	if (!FFileHelper::LoadFileToString(Json, *(DataDir / TEXT("atlas.json"))))
	{
		OutError = TEXT("cannot read atlas.json");
		LoadError = OutError;
		return false;
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		OutError = TEXT("atlas.json is not valid JSON");
		LoadError = OutError;
		return false;
	}
	const TSharedPtr<FJsonObject>* FrameObj = nullptr;
	if (!Root->TryGetObjectField(TEXT("frames"), FrameObj))
	{
		OutError = TEXT("atlas.json has no frames table");
		LoadError = OutError;
		return false;
	}
	// Each frame is [x, y, w, h] on the page, the same four numbers both other
	// runtimes index it by.
	for (const TPair<FString, TSharedPtr<FJsonValue>>& Pair : (*FrameObj)->Values)
	{
		const TArray<TSharedPtr<FJsonValue>>* Nums = nullptr;
		if (!Pair.Value->TryGetArray(Nums) || Nums->Num() < 4)
		{
			continue;
		}
		FRivenFrame Frame;
		Frame.X = (int32)(*Nums)[0]->AsNumber();
		Frame.Y = (int32)(*Nums)[1]->AsNumber();
		Frame.W = (int32)(*Nums)[2]->AsNumber();
		Frame.H = (int32)(*Nums)[3]->AsNumber();
		Frames.Add(Pair.Key, Frame);
		Brushes.Add(Pair.Key, MakeBrush(AtlasTexture, AtlasSize,
			FIntRect(Frame.X, Frame.Y, Frame.X + Frame.W, Frame.Y + Frame.H)));
	}
	if (Frames.Num() == 0)
	{
		OutError = TEXT("atlas.json named no sprites");
		LoadError = OutError;
		return false;
	}

	if (!BuildFont(DataDir / TEXT("font.json"), OutError))
	{
		LoadError = OutError;
		return false;
	}

	bLoaded = true;
	return true;
}

FIntPoint FRivenbrookArt::FrameSize(const FString& Name) const
{
	if (const FRivenFrame* Frame = Frames.Find(Name))
	{
		return FIntPoint(Frame->W, Frame->H);
	}
	return FIntPoint::ZeroValue;
}

void FRivenbrookArt::Spr(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo,
	const FString& Name, const FVector2f& Pos, float Scale,
	const FLinearColor& Tint) const
{
	const FSlateBrush* Brush = Brushes.Find(Name);
	const FRivenFrame* Frame = Frames.Find(Name);
	if (Brush == nullptr || Frame == nullptr)
	{
		return;
	}
	// Rounded, because a sprite half a pixel off is a sprite with a seam.
	const FVector2f Size(Frame->W * Scale, Frame->H * Scale);
	FSlateDrawElement::MakeBox(Out, Layer,
		Geo.ToPaintGeometry(Size, FSlateLayoutTransform(
			FVector2f(FMath::RoundToFloat(Pos.X), FMath::RoundToFloat(Pos.Y)))),
		Brush, ESlateDrawEffect::NoPixelSnapping, Tint);
}

void FRivenbrookArt::SprStretched(FSlateWindowElementList& Out, int32 Layer,
	const FGeometry& Geo, const FString& Name, const FVector2f& Pos,
	const FVector2f& Size, const FIntRect& Part) const
{
	const FRivenFrame* Frame = Frames.Find(Name);
	if (Frame == nullptr)
	{
		return;
	}
	const FIntRect Region(
		Frame->X + Part.Min.X, Frame->Y + Part.Min.Y,
		Frame->X + (Part.Max.X > Part.Min.X ? Part.Max.X : Frame->W),
		Frame->Y + (Part.Max.Y > Part.Min.Y ? Part.Max.Y : Frame->H));
	const FSlateBrush Brush = MakeBrush(AtlasTexture, AtlasSize, Region);
	FSlateDrawElement::MakeBox(Out, Layer,
		Geo.ToPaintGeometry(Size, FSlateLayoutTransform(Pos)),
		&Brush, ESlateDrawEffect::NoPixelSnapping, FLinearColor::White);
}

void FRivenbrookArt::SprFoot(FSlateWindowElementList& Out, int32 Layer,
	const FGeometry& Geo, const FString& Name, const FVector2f& Foot, float Scale,
	const FLinearColor& Tint) const
{
	const FIntPoint Size = FrameSize(Name);
	if (Size == FIntPoint::ZeroValue)
	{
		return;
	}
	Spr(Out, Layer, Geo, Name,
		FVector2f(Foot.X - Size.X * Scale / 2.0f, Foot.Y - Size.Y * Scale), Scale, Tint);
}

float FRivenbrookArt::ScaleFor(const FString& Name, float TargetH,
	const TArray<float>& Steps) const
{
	const FIntPoint Size = FrameSize(Name);
	if (Size.Y <= 0)
	{
		return 1.0f;
	}
	float Best = 1.0f;
	float BestErr = TNumericLimits<float>::Max();
	for (const float Step : Steps)
	{
		const float Err = FMath::Abs(Size.Y * Step - TargetH);
		if (Err < BestErr)
		{
			BestErr = Err;
			Best = Step;
		}
	}
	return Best;
}

void FRivenbrookArt::Rect(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo,
	const FVector2f& Pos, const FVector2f& Size, const FLinearColor& Color) const
{
	FSlateDrawElement::MakeBox(Out, Layer,
		Geo.ToPaintGeometry(Size, FSlateLayoutTransform(Pos)),
		FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")),
		ESlateDrawEffect::NoPixelSnapping, Color);
}

void FRivenbrookArt::Text(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo,
	const FString& S, const FVector2f& Pos, const FLinearColor& Color,
	const FString& Align, bool bShadow) const
{
	float X = FMath::RoundToFloat(Pos.X);
	const float Y = FMath::RoundToFloat(Pos.Y);
	if (Align == TEXT("center"))
	{
		X -= FMath::RoundToFloat(TextWidth(S) / 2.0f);
	}
	else if (Align == TEXT("right"))
	{
		X -= TextWidth(S);
	}

	for (int32 Pass = bShadow ? 0 : 1; Pass < 2; ++Pass)
	{
		const float Off = Pass == 0 ? 1.0f : 0.0f;
		const FLinearColor Ink = Pass == 0 ? TextShadow : Color;
		for (int32 i = 0; i < S.Len(); ++i)
		{
			const int32* Column = Glyphs.Find(S[i]);
			if (Column == nullptr || !GlyphBrushes.IsValidIndex(*Column))
			{
				continue;
			}
			FSlateDrawElement::MakeBox(Out, Layer,
				Geo.ToPaintGeometry(FVector2f(GlyphW, GlyphH), FSlateLayoutTransform(
					FVector2f(X + i * GlyphW + Off, Y + Off))),
				&GlyphBrushes[*Column], ESlateDrawEffect::NoPixelSnapping, Ink);
		}
	}
}
