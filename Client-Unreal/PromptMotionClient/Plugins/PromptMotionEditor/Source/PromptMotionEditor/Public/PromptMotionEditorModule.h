#pragma once

#include "Modules/ModuleInterface.h"

class FPromptMotionEditorModule final : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

private:
	void RegisterMenus();
	void OpenPromptMotionTab();
};
