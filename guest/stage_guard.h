#ifndef TA_STAGE_GUARD_H
#define TA_STAGE_GUARD_H
// Keep staging SET objects, exits, enemies and deathzones out of the mirror.
// Tasks remain allocated; their normal updates resume when mirror ownership ends.
struct TA_StageTask {ObjectMaster* object;ObjectFuncPtr main;};
static TA_StageTask stageTasks[4096];
static unsigned stageTaskCount;
static void __cdecl ta_stage_guard(ObjectMaster* obj) {
    if (originalStageTable) return;
    for (unsigned i=0;i<stageTaskCount;i++) if (stageTasks[i].object==obj) {
        stageTasks[i].main(obj);return;
    }
}
static void ta_guard_stage_tasks() {
    if (!originalStageTable) return;
    auto lists=reinterpret_cast<ObjectMaster**>(0x3ABDBC4);
    for (unsigned index=0;index<8;index++) {
        ObjectMaster* obj=lists[index];
        for (unsigned visits=0;obj && visits<4096;visits++,obj=obj->Next) {
            if (obj==hookedPlayer || !obj->MainSub || obj->MainSub==ta_stage_guard ||
                (!obj->SETData.SETData && obj->MainSub!=reinterpret_cast<ObjectFuncPtr>(0x44AE80))) continue;
            unsigned i=0;
            for (;i<stageTaskCount;i++) if (stageTasks[i].object==obj) break;
            if (i==stageTaskCount) {if (stageTaskCount==4096) continue;stageTaskCount++;}
            stageTasks[i]={obj,obj->MainSub};obj->MainSub=ta_stage_guard;
        }
    }
}
#endif
