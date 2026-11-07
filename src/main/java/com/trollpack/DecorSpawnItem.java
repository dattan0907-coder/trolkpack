package com.trollpack;

import com.trollpack.entity.DecorEntity;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.phys.Vec3;

import java.util.function.Supplier;

/** Places a decor entity on the clicked block (decor entities are not Mobs, so SpawnEggItem can't be used). */
public class DecorSpawnItem extends Item {
    private final Supplier<? extends EntityType<? extends DecorEntity>> type;

    public DecorSpawnItem(Supplier<? extends EntityType<? extends DecorEntity>> type, Properties props) {
        super(props);
        this.type = type;
    }

    @Override
    public InteractionResult useOn(UseOnContext ctx) {
        if (!(ctx.getLevel() instanceof ServerLevel level)) return InteractionResult.SUCCESS;
        BlockPos pos = ctx.getClickedPos().relative(ctx.getClickedFace());
        DecorEntity e = type.get().create(level);
        if (e == null) return InteractionResult.FAIL;
        float yaw = Math.round(ctx.getRotation() / 90f) * 90f;
        e.moveTo(Vec3.atBottomCenterOf(pos).x, pos.getY(), Vec3.atBottomCenterOf(pos).z, yaw, 0);
        level.addFreshEntity(e);
        if (ctx.getPlayer() == null || !ctx.getPlayer().getAbilities().instabuild) ctx.getItemInHand().shrink(1);
        return InteractionResult.CONSUME;
    }
}
