#include "RivenbrookModule.h"

#include "SRivenbrookView.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Docking/TabManager.h"
#include "Widgets/Docking/SDockTab.h"
#include "WorkspaceMenuStructure.h"
#include "WorkspaceMenuStructureModule.h"

#define LOCTEXT_NAMESPACE "Rivenbrook"

const FName FRivenbrookModule::TabName(TEXT("Rivenbrook"));

void FRivenbrookModule::StartupModule()
{
	FGlobalTabmanager::Get()
		->RegisterNomadTabSpawner(TabName, FOnSpawnTab::CreateLambda(
			[](const FSpawnTabArgs&) -> TSharedRef<SDockTab>
			{
				return SNew(SDockTab)
					.TabRole(ETabRole::NomadTab)
					[
						SNew(SRivenbrookView)
					];
			}))
		.SetDisplayName(LOCTEXT("TabTitle", "Rivenbrook"))
		.SetTooltipText(LOCTEXT("TabTooltip", "The game, drawn from the cooked assets."))
		.SetGroup(WorkspaceMenu::GetMenuStructure().GetDeveloperToolsMiscCategory());
}

void FRivenbrookModule::ShutdownModule()
{
	if (FSlateApplication::IsInitialized())
	{
		FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(TabName);
	}
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FRivenbrookModule, Rivenbrook)
