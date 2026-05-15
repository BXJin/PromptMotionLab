#include "PromptMotionEditorModule.h"

#include "LevelEditor.h"
#include "ToolMenus.h"
#include "UI/SMotionLabPanel.h"
#include "Widgets/Docking/SDockTab.h"

#define LOCTEXT_NAMESPACE "PromptMotionEditor"

namespace PromptMotionEditor
{
	static const FName TabId("PromptMotionEditor.Panel");
}

void FPromptMotionEditorModule::StartupModule()
{
	FGlobalTabmanager::Get()->RegisterNomadTabSpawner(
		PromptMotionEditor::TabId,
		FOnSpawnTab::CreateLambda([](const FSpawnTabArgs&)
		{
			return SNew(SDockTab)
				.TabRole(ETabRole::NomadTab)
				[
					SNew(SMotionLabPanel)
				];
		}))
		.SetDisplayName(LOCTEXT("PromptMotionTabTitle", "Prompt Motion Lab"))
		.SetMenuType(ETabSpawnerMenuType::Hidden);

	UToolMenus::RegisterStartupCallback(
		FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FPromptMotionEditorModule::RegisterMenus));
}

void FPromptMotionEditorModule::ShutdownModule()
{
	if (UToolMenus::IsToolMenuUIEnabled())
	{
		UToolMenus::UnRegisterStartupCallback(this);
		UToolMenus::UnregisterOwner(this);
	}

	FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(PromptMotionEditor::TabId);
}

void FPromptMotionEditorModule::RegisterMenus()
{
	FToolMenuOwnerScoped OwnerScoped(this);

	UToolMenu* Menu = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Window");
	FToolMenuSection& Section = Menu->FindOrAddSection("WindowLayout");
	Section.AddMenuEntry(
		"OpenPromptMotionLab",
		LOCTEXT("OpenPromptMotionLabLabel", "Prompt Motion Lab"),
		LOCTEXT("OpenPromptMotionLabTooltip", "Open the Prompt Motion Lab editor panel."),
		FSlateIcon(),
		FUIAction(FExecuteAction::CreateRaw(this, &FPromptMotionEditorModule::OpenPromptMotionTab)));
}

void FPromptMotionEditorModule::OpenPromptMotionTab()
{
	FGlobalTabmanager::Get()->TryInvokeTab(PromptMotionEditor::TabId);
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FPromptMotionEditorModule, PromptMotionEditor)
