# Disk Benchmarks

Date: 2026-02-25. Test: `dd` with `oflag=direct` / `iflag=direct`.

## Comparison

| Host | Disk | Write | Read |
|---|---|---|---|
| **rpi4** (legacy) | SanDisk 3.2Gen1 114.6 GB (USB) | 60.7 MB/s | 151 MB/s |
| **rpi5** | microSD 117 GB (new, 64-bit OS) | 73.5 MB/s | 94.5 MB/s |
| **blackops** | Samsung 990 PRO 1TB (NVMe) | 4.4 GB/s | 15.2 GB/s* |

> *blackops: abnormally high read speed — data was cached in RAM.

## rpi4 (legacy)

- **Disk:** SanDisk 3.2Gen1 114.6 GB (USB flash)
- **Test:** 256 MB

| Operation | Speed |
|---|---|
| Write | 60.7 MB/s |
| Read | 151 MB/s |

## rpi5

- **Disk:** microSD 117 GB (new card after 64-bit OS reinstall)
- **Test:** 256 MB, conv=fdatasync / drop_caches
- **Date:** 2026-02-25

| Operation | Speed |
|---|---|
| Write | 73.5 MB/s |
| Read | 94.5 MB/s |

## blackops

- **Disks:** Samsung SSD 990 PRO 1TB (NVMe) + HP SSD FX900 Plus 2TB (NVMe)
- **Test:** 1024 MB

| Operation | Speed |
|---|---|
| Write | 4.4 GB/s |
| Read | 15.2 GB/s |

> Note: blackops shows abnormally high read speed — data was likely cached in RAM.
