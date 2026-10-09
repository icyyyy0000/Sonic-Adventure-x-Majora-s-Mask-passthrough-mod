#include <stdio.h>
#include "z64bgcheck.h"
int main(void) {
    for (unsigned index = 0; index < 8192; index++) {
        unsigned solid = COLPOLY_VTX(index, COLPOLY_IGNORE_NONE);
        unsigned ignored = COLPOLY_VTX(index, COLPOLY_IGNORE_ENTITY);
        if (COLPOLY_VIA_FLAG_TEST(solid, COLPOLY_IGNORE_ENTITY)) return 1;
        if (!COLPOLY_VIA_FLAG_TEST(ignored, COLPOLY_IGNORE_ENTITY)) return 2;
        if (COLPOLY_VTX_INDEX(ignored) != index) return 3;
    }
    if (!(COLPOLY_VTX(2, 0) & COLPOLY_IGNORE_ENTITY)) return 4;
    if (COLPOLY_VTX(0, COLPOLY_IGNORE_ENTITY) & COLPOLY_IGNORE_ENTITY) return 5;
    puts("PASS: all 8192 packed vertex indices retain solid geometry; only actual entity exclusions are skipped.");
    return 0;
}
