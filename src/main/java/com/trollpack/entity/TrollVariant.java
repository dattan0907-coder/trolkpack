package com.trollpack.entity;

import net.minecraft.util.RandomSource;
import java.util.Set;

/**
 * Appearance of a troll, replacing MythicMobs' TROLL_randomizer / changepart skills.
 * Every field maps to one alt bone of troll.geo.json (see tools/model_meta.json "alt_bones").
 * Packed into one int so it can be synced as a single entity data value.
 */
public record TrollVariant(int skin, boolean fem, int head, boolean tusk1, boolean tusk2,
                           boolean spear, boolean shield, boolean armorL, boolean armorR) {

    private static final int[] MAX_HEAD = {13, 14, 14};
    /** heads that only fit male bodies (from the TROLL_head_<skin>_<n> conditions), default fem head is 12 */
    private static final Set<Integer>[] MALE_ONLY = new Set[]{Set.of(1, 4, 5, 7, 8), Set.of(1, 2, 5, 6, 8, 9), Set.of(1, 2, 5, 6, 8, 9)};

    public static TrollVariant random(RandomSource r) {
        int skin = r.nextInt(3);
        boolean fem = r.nextBoolean();
        int head = 1 + r.nextInt(MAX_HEAD[skin]);
        if (fem && MALE_ONLY[skin].contains(head)) head = 12;
        boolean spear = r.nextFloat() < 0.75f;
        boolean shield = spear && r.nextFloat() < 0.5f;
        return new TrollVariant(skin, fem, head, r.nextBoolean(), r.nextBoolean(), spear, shield, r.nextBoolean(), r.nextBoolean());
    }

    public int pack() {
        return skin | (fem ? 4 : 0) | (head << 3) | (tusk1 ? 1 << 8 : 0) | (tusk2 ? 1 << 9 : 0) | (spear ? 1 << 10 : 0)
                | (shield ? 1 << 11 : 0) | (armorL ? 1 << 12 : 0) | (armorR ? 1 << 13 : 0);
    }

    public static TrollVariant unpack(int v) {
        return new TrollVariant(Math.min(2, v & 3), (v & 4) != 0, Math.max(1, (v >> 3) & 31), (v & 1 << 8) != 0, (v & 1 << 9) != 0,
                (v & 1 << 10) != 0, (v & 1 << 11) != 0, (v & 1 << 12) != 0, (v & 1 << 13) != 0);
    }
}
