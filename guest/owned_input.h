#ifndef TA_OWNED_INPUT_H
#define TA_OWNED_INPUT_H
// Run before Character Select's OnInput: its raw-pad D button toggles input
// redirection and its other chords select/teleport staging players.
static void ta_clear_owned_pad(ControllerData& pad) {
    pad={};pad.NotHeldButtons=~0u;
}
// Zelda owns Start while the companion is driving a foreign-world task.
// Keep the shared controller from independently pausing the SADX simulation.
static void ta_filter_owned_start(ControllerData& pad,int& held,int& pressed) {
    pad.HeldButtons &= ~Buttons_Start;
    pad.NotHeldButtons |= Buttons_Start;
    pad.PressedButtons &= ~Buttons_Start;
    pad.ReleasedButtons &= ~Buttons_Start;
    held &= ~Buttons_Start;
    pressed &= ~Buttons_Start;
}
#endif
