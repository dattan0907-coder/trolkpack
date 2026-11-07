package com.trollpack.entity;

import com.trollpack.TrollPack;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.projectile.ThrowableItemProjectile;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.Vec3;

import java.util.UUID;

/** Thrown troll spear (damage 20) or the voodoo "skull" tracking missile (damage 15 + chain, slow, knock-up). */
public class SpearProjectile extends ThrowableItemProjectile {
    private final boolean missile;
    private UUID targetId;
    private int life;

    public SpearProjectile(EntityType<? extends SpearProjectile> type, Level level) { this(type, level, false); }

    public SpearProjectile(EntityType<? extends SpearProjectile> type, Level level, boolean missile) {
        super(type, level);
        this.missile = missile;
    }

    public void setTarget(LivingEntity e) { targetId = e.getUUID(); }

    @Override protected Item getDefaultItem() { return missile ? TrollPack.VOODOO_SKULL.get() : TrollPack.TROLL_SPEAR.get(); }
    @Override protected double getDefaultGravity() { return missile ? 0 : 0.04; }

    @Override
    protected boolean canHitEntity(Entity e) { return !(e instanceof TrollEntity) && super.canHitEntity(e); }

    @Override
    public void tick() {
        super.tick();
        if (missile) {
            if (!level().isClientSide && targetId != null && level() instanceof net.minecraft.server.level.ServerLevel sl
                    && sl.getEntity(targetId) instanceof LivingEntity t && t.isAlive()) {
                Vec3 want = t.position().add(0, t.getBbHeight() * 0.5, 0).subtract(position()).normalize().scale(0.55);
                setDeltaMovement(getDeltaMovement().scale(0.75).add(want.scale(0.25)).normalize().scale(0.55));
                hasImpulse = true;
            }
            if (level().isClientSide) {
                level().addParticle(ParticleTypes.SOUL_FIRE_FLAME, getX(), getY(), getZ(), 0, 0, 0);
                level().addParticle(ParticleTypes.SQUID_INK, getX(), getY(), getZ(), 0, 0.05, 0);
            }
            if (++life > 100 && !level().isClientSide) discard();
        }
    }

    @Override
    protected void onHitEntity(EntityHitResult r) {
        if (level().isClientSide) return;
        Entity e = r.getEntity();
        if (missile) {
            hitMissile(e, true);
        } else {
            e.hurt(damageSources().thrown(this, getOwner()), 20);
            impact();
        }
        discard();
    }

    private void hitMissile(Entity e, boolean chain) {
        if (!(e instanceof LivingEntity le)) return;
        le.hurt(damageSources().indirectMagic(this, getOwner()), 15);
        le.push(0, 0.9, 0);
        le.hurtMarked = true;
        le.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 120, 1));
        if (level() instanceof net.minecraft.server.level.ServerLevel sl)
            sl.sendParticles(ParticleTypes.SQUID_INK, le.getX(), le.getY() + 1, le.getZ(), 15, 0.25, 0.25, 0.25, 0.1);
        if (!chain) return;
        // TROLL_voodoo_spell_chain: every other non-troll living entity within 12 blocks gets hit as well
        for (LivingEntity o : level().getEntitiesOfClass(LivingEntity.class, new AABB(le.blockPosition()).inflate(12),
                x -> x != le && !(x instanceof TrollEntity) && x.isAlive() && x != getOwner())) {
            hitMissile(o, false);
        }
    }

    private void impact() {
        level().playSound(null, blockPosition(), TrollPack.IMPACT.get(random.nextInt(TrollPack.IMPACT.size())).get(), SoundSource.HOSTILE, 1f, 1f);
    }

    @Override
    protected void onHitBlock(BlockHitResult r) {
        super.onHitBlock(r);
        if (level().isClientSide) return;
        if (!missile && random.nextFloat() < 0.5f) spawnAtLocation(TrollPack.TROLL_SPEAR.get()); // groundspear
        discard();
    }
}
