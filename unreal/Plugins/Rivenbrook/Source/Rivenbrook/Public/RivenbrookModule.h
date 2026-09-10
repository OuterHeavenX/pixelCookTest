#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleInterface.h"

/** Registers a tab that hosts the game. An editor tab rather than a level and
 *  a game mode, because a tab needs no assets at all - no .umap, no Blueprint,
 *  nothing that has to be authored inside Unreal - so the entire third runtime
 *  stays text in this repository, the same as the other two. */
class FRivenbrookModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

	static const FName TabName;
};
