#ifndef TA_EMOTE_POSE_H
#define TA_EMOTE_POSE_H
// Canonical idle hierarchies only. No root, leg or collision transforms change.
static void ta_emote_turn(s16* angle,s16 target,f32 weight){*angle+=(s16)((s16)(target-*angle)*weight);}
static void ta_emote_pose(u32 character,s32 bone,s32 frame,Vec3s* rot){
    if(frame<1 || frame>40)return;
    f32 weight=frame<8 ? frame/8.0f : frame>32 ? (40-frame)/8.0f : 1.0f;
    f32 wave=Math_SinS(frame*4500);
    if(character==TA_SONIC){
        if(bone==36)ta_emote_turn(&rot->z,0x5000,weight);
        if(bone==37)ta_emote_turn(&rot->z,0x1000,weight);
        if(bone==38)rot->x+=(s16)(wave*0x1800*weight);
    }else if(character==TA_TAILS){
        if(bone==59 || bone==63){rot->x+=(s16)((bone==59 ? 1 : -1)*wave*0x1800*weight);rot->z+=(s16)(0x800*weight);}
    }else if(character==TA_KNUCKLES){
        if(bone==35)ta_emote_turn(&rot->z,0x3000+wave*0x800,weight);
        if(bone==36)ta_emote_turn(&rot->z,0x2000,weight);
        if(bone==37)rot->x+=(s16)(wave*0x800*weight);
    }else if(character==TA_AMY){
        if(bone==27)ta_emote_turn(&rot->z,0x2000,weight);
        if(bone==28)ta_emote_turn(&rot->z,0x2000,weight);
        if(bone==29){ta_emote_turn(&rot->z,0,weight);rot->x+=(s16)(wave*0x800*weight);}
        if(bone==35)ta_emote_turn(&rot->z,(s16)0x8000,weight);
    }else if(character==TA_GAMMA){
        if(bone==41)ta_emote_turn(&rot->z,-0x1800,weight);
        if(bone==42)ta_emote_turn(&rot->z,0x6000,weight);
        if(bone==43){ta_emote_turn(&rot->z,0,weight);rot->y+=(s16)(wave*0x600*weight);}
    }
}
#endif
