#include <windows.h>
#include <string>
#include "SADXModInfo.h"
#include "character_select.h"
int main() {
    unsigned expected[] = {0,Buttons_Z|Buttons_Left,Buttons_Z|Buttons_R,Buttons_Z|Buttons_Down,
        Buttons_Z|Buttons_Right,Buttons_Z|Buttons_Up,Buttons_Z|Buttons_L};
    for (unsigned i=0;i<7;i++) if (ta_selection_buttons(i)!=expected[i]) return 1;
    if (ta_selection_buttons(7) || ta_selection_buttons(0xffffffffu)) return 2;
    return 0;
}
