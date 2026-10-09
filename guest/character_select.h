#ifndef TA_GUEST_SELECT_H
#define TA_GUEST_SELECT_H
// Selection chords understood by the user's installed X-Hax Character Select.
// This requests its complete original task swap, rather than changing CharID.
static unsigned ta_selection_buttons(unsigned character) {
    switch (character) {
    case 1: return Buttons_Z | Buttons_Left;
    case 2: return Buttons_Z | Buttons_R;
    case 3: return Buttons_Z | Buttons_Down;
    case 4: return Buttons_Z | Buttons_Right;
    case 5: return Buttons_Z | Buttons_Up;
    case 6: return Buttons_Z | Buttons_L;
    default: return 0;
    }
}
#endif
