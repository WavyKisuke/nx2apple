#pragma once
#include <stdbool.h>
#include <stdint.h>

#if defined(__APPLE__)
#define DM_RAM_DONOR_WEAK __attribute__((weak_import))
#else
#define DM_RAM_DONOR_WEAK __attribute__((weak))
#endif

void *mlx_ram_donor_acquire_up_to(uint64_t size, uint64_t minimum, uint64_t *actual) DM_RAM_DONOR_WEAK;
bool mlx_ram_donor_map_region(void *base, void *target, uint64_t size) DM_RAM_DONOR_WEAK;
void mlx_ram_donor_release(void *base) DM_RAM_DONOR_WEAK;
void mlx_ram_donor_shutdown(void) DM_RAM_DONOR_WEAK;
void mlx_ram_donor_set_kill_after_mapping(bool enabled) DM_RAM_DONOR_WEAK;
const char *mlx_ram_donor_last_error(void) DM_RAM_DONOR_WEAK;
void mlx_ram_donor_set_status(const char *status) DM_RAM_DONOR_WEAK;
