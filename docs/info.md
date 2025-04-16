<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works
## SPI Interface

### Key Features

* **Mode 0**: Data sampled on rising `SCLK` edge, valid on falling edge.
* **No CIPO**: Read operations are ignored; only writes are supported.
* **Clock Domain Crossing (CDC)**: Synchronized using a 2-stage flip-flop chain to prevent metastability.
* **Fixed Transaction Length**: 16 clock cycles per transaction (1 R/W bit + 7 address bits + 8 data bits).

| Field | R/W Bit (1b) | Address (7b) | Data (8b) |
|----|----|----|----|
| **Description** | `1` = Write,`0` = Read (ignored) | Valid: `0x00-0x04` | Data to write |


* Example Transaction
  * **Write to** `0x00` **with** `0xF0`:
    * Bitstream: 1 (Write) + 0000000 (Addr `0x00`) + 11110000 (Data `0xF0`).

## Register Map

| Addr | Register | Description | Reset Value |
|----|----|----|----|
| `0x00` | `en_reg_out_7_0` | Enable outputs on `uo_out[7:0]`   | `0x00`   |
| `0x01` | `en_reg_out_15_8` | Enable outputs on `uio_out[7:0]`   | `0x00`   |
| `0x02` | `en_reg_pwm_7_0` | Enable PWM for `uo_out[7:0]`   | `0x00`   |
| `0x03` | `en_reg_pwm_15_8` | Enable PWM for `uio_out[7:0]`   | `0x00`   |
| `0x04` | `pwm_duty_cycle` | PWM Duty Cycle ( `0x00`=0%, `0xFF`=100%) | `0x00`   |

### Output Behavior

| Output Enable Bit | PWM Mode Bit | Result |
|----|----|----|
| `0` | `X` | Output `0` |
| `1` | `0` | Output `1` |
| `1` | `1` | Output PWM |

Note: Output Enable Takes Precedence over PWM Mode


---

## PWM Peripheral

### Specifications

* **Frequency**: 3 kHz (derived from 10 MHz clock using a divider).
* **Duty Cycle**: Controlled by `pwm_duty_cycle` register (`0x04`).
  * Duty cycle = `(pwm_duty_cycle / 256) * 100%`.
  * Special case for `pwm_duty_cycle == 255`, force output to be `1`.
* **Output Structure**:
  * 16-bit output: `{uio_out[7:0], uo_out[7:0]}`.
  * Each bit can be independently enabled for static output or PWM.


---

## Clock Domain Crossing (CDC)

* **SPI Signals**: `nCS`, `SCLK`, and `COPI` are synchronized using a 2-stage flip-flop chain.
* **Edge Detection**:
  * Transaction starts on `nCS` falling edge.
  * Data captured on `SCLK` rising edge.
Explain how your project works

## How to test

### SPI Testbench (Provided)

* **Coverage**:
  * Valid/invalid address handling.
  * Register write.
  * Output assertions for `uo_out` and `uio_out`.
  * Gives you a helper function to execute an SPI transaction

### PWM Testbench (One of your deliverables)

* **Scenarios to Test**:

  
  1. Duty cycle sweep (`0x00` to `0xFF`).
  2. Interaction between Output Enable and PWM Enable registers.
  3. Frequency verification (\~3 kHz +/- 1%).
  4. PWM Duty verification (+/-1%).
Explain how to use your project

## External hardware

List external hardware used in your project (e.g. PMOD, LED display, etc), if any
