#pragma once
#include <stdbool.h>
#include <stdint.h>

// Native host regression tests provide local donor stubs. Do not mark those
// definitions as weak imports: Apple's linker otherwise leaves their
// references unresolved even though the test translation unit defines them.
#if defined(DM_RAM_DONOR_TEST_STUB)
#define DM_RAM_DONOR_WEAK
#define DM_RAM_DONOR_AVAILABLE(function) (1)
#elif defined(__APPLE__)
#define DM_RAM_DONOR_WEAK __attribute__((weak_import))
#else
#define DM_RAM_DONOR_WEAK __attribute__((weak))
#endif

#ifndef DM_RAM_DONOR_AVAILABLE
#define DM_RAM_DONOR_AVAILABLE(function) ((function) != NULL)
#endif

void *mlx_ram_donor_acquire_up_to(uint64_t size, uint64_t minimum, uint64_t *actual) DM_RAM_DONOR_WEAK;
bool mlx_ram_donor_map_region(void *base, void *target, uint64_t size) DM_RAM_DONOR_WEAK;
void mlx_ram_donor_release(void *base) DM_RAM_DONOR_WEAK;
void mlx_ram_donor_shutdown(void) DM_RAM_DONOR_WEAK;
void mlx_ram_donor_set_kill_after_mapping(bool enabled) DM_RAM_DONOR_WEAK;
const char *mlx_ram_donor_last_error(void) DM_RAM_DONOR_WEAK;
void mlx_ram_donor_set_status(const char *status) DM_RAM_DONOR_WEAK;
