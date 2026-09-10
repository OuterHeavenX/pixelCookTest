// The third runtime. Slate for drawing, Json for the cooked rules, and
// ImageWrapper to read the atlas PNG off disk - the same PNG the other two
// builds read, not an imported .uasset copy of it.
using UnrealBuildTool;

public class Rivenbrook : ModuleRules
{
	public Rivenbrook(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"Slate",
			"SlateCore",
			"InputCore",
			"Json",
			"JsonUtilities",
			"ImageWrapper",
			"RenderCore",
			"RHI",
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"UnrealEd",
			"WorkspaceMenuStructure",
			"ToolMenus",
			"Projects",
		});
	}
}
