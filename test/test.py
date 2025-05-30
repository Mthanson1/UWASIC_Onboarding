# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

async def PWM_test(dut, signal, channel, num_cycles=3, timeout=5000000):
    """
    Sample and return freq and DC of PWM output
    """
    last_val = (int(signal.value) >> channel) & 1

    rising_edge = []
    time_high = []

    last_rise = None

    start_time = cocotb.utils.get_sim_time(units="ns")

    while len(rising_edge) - 1 < num_cycles:
        await ClockCycles(dut.clk, 1)
        now = cocotb.utils.get_sim_time(units="ns")

        curr_val = (int(signal.value) >> channel) & 1
        
        if now - start_time > timeout:
            return 1.0 if curr_val == 1 else 0.0, 0
        
        if curr_val == 1 and last_val == 0:
            #rising edge
            rising_edge.append(now)
            
            last_rise = now
        elif curr_val == 0 and last_val == 1:
            #falling edge
            if last_rise is not None:
                time_high.append(now - last_rise)
        
        last_val = curr_val

    periods = []
    for t1, t2 in zip(rising_edge, rising_edge[1:]):
        periods.append(t2-t1)

    avg_period = sum(periods)/len(periods)
    avg_tHigh = sum(time_high)/len(time_high)

    if avg_period > 0:
        duty = avg_tHigh/avg_period
        freq = (1E9)/avg_period
    else:
        duty = 0
        freq = 0
    
    return duty, freq

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior - SPI")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    # Write your test here

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior - PWM Freq")

    #set DC to 50% for measuring freq:
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x80)

    for i in range(8):
        #enable proper input and set to pwm mode
        ui_in_val = await send_spi_transaction(dut, 1, 0x00, 1 << i)
        ui_in_val = await send_spi_transaction(dut, 1, 0x02, 1 << i)

        duty, freq = await PWM_test(dut, dut.uo_out, i)
        assert 2970 < freq < 3030, f"Expected Freq: 2970-3030Hz | Recieved: {freq}Hz on channel {i}"
        
        #reset output channel
        ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0)
        ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0)

    for i in range(8):
        #enable proper input and set to pwm mode
        ui_in_val = await send_spi_transaction(dut, 1, 0x01, 1 << i)
        ui_in_val = await send_spi_transaction(dut, 1, 0x03, 1 << i)

        duty, freq = await PWM_test(dut, dut.uio_out, i)
        assert 2970 < freq < 3030, f"Expected Freq: 2970-3030Hz | Recieved: {freq}Hz on channel {i + 8}"
        
        #reset output channel
        ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0)
        ui_in_val = await send_spi_transaction(dut, 1, 0x03, 0)

    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0)

    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    # Write your test here
    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior - PWM Duty Cycle")

    for i in range(8):
        #enable proper input and set to pwm mode
        ui_in_val = await send_spi_transaction(dut, 1, 0x00, 1 << i)
        ui_in_val = await send_spi_transaction(dut, 1, 0x02, 1 << i)

        #0% DC Test:
        ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)

        duty, freq = await PWM_test(dut, dut.uo_out, i)
        assert abs(duty - 0.0) < 0.001 , f"Expected DC: 0% | Recieved: {duty * 100}% on channel {i}"
        
        #50% DC Test:
        ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x80)

        duty, freq = await PWM_test(dut, dut.uo_out, i)
        assert abs(duty - 0.5) < 0.001, f"Expected DC: 50% | Recieved: {duty * 100}% on channel {i}"

        #100% DC Test:
        ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)

        duty, freq = await PWM_test(dut, dut.uo_out, i)
        assert abs(duty - 1.0) < 0.001, f"Expected DC: 100% | Recieved: {duty * 100}% on channel {i}"

        #reset output channel
        ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0)
        ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0)

    for i in range(8):
        #enable proper input and set to pwm mode
        ui_in_val = await send_spi_transaction(dut, 1, 0x01, 1 << i)
        ui_in_val = await send_spi_transaction(dut, 1, 0x03, 1 << i)

        #0% DC Test:
        ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)

        duty, freq = await PWM_test(dut, dut.uio_out, i)
        assert abs(duty - 0.0) < 0.001, f"Expected DC: 0% | Recieved: {duty * 100}% on channel {i + 8}"

        #50% DC Test:
        ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x80)

        duty, freq = await PWM_test(dut, dut.uio_out, i)
        assert abs(duty - 0.5) < 0.001, f"Expected DC: 50% | Recieved: {duty * 100}% on channel {i + 8}"

        #100% DC Test:
        ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)

        duty, freq = await PWM_test(dut, dut.uio_out, i)
        assert abs(duty - 1.0) < 0.001, f"Expected DC: 100% | Recieved: {duty * 100}% on channel {i + 8}"
        
        #reset output channel
        ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0)
        ui_in_val = await send_spi_transaction(dut, 1, 0x03, 0)

    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0)

    dut._log.info("PWM Duty Cycle test completed successfully")
