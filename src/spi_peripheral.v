`default_nettype none

module spi_peripheral (
    input wire COPI,
    input wire SCLK,
    input wire nCS,
    input clk,
    input rst_n,
    output reg [7:0] en_reg_out_7_0,
    output reg [7:0] en_reg_out_15_8,
    output reg [7:0] en_reg_pwm_7_0,
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle
);

reg [2:0] sync_COPI, sync_SCLK, sync_nCS;

always @(posedge clk or negedge rst_n) begin //3 dff synchronization chain for external input
    if(~rst_n) begin
        sync_COPI <= 3'b000;
        sync_SCLK <= 3'b000;
        sync_nCS <= 3'b111;
    end else begin
        sync_COPI <= {sync_COPI[1:0], COPI};
        sync_SCLK <= {sync_SCLK[1:0], SCLK};
        sync_nCS <= {sync_nCS[1:0], nCS};
    end
end 

wire SCLK_rise = sync_SCLK[1] & ~sync_SCLK[2];
wire nCS_rise = sync_nCS[1] & ~sync_nCS[2];
wire nCS_fall = ~sync_nCS[1] & sync_nCS[2];

wire [3:0] _unused;
reg [15:0] packet;


wire address_decoded = packet[15] & ~|packet[14:12] & (packet[11:8] < 5);
reg transaction_ready, transaction_processed;
reg [4:0] clk_count;
reg [3:0] address;
reg [7:0] data;

//process SPI protocol in clk domain 
always @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin //reset peripheral

        clk_count <= 4'b0;
        transaction_ready <= 1'b0;
        packet <= 15'b0;

    end else if (sync_nCS[1] == 1'b0) begin //nCS is low so start counting clock cycles.
        
        if(nCS_fall) clk_count <= 4'd0;
        if(SCLK_rise) begin
            clk_count <= clk_count + 1;
            packet <= {packet[14:0], sync_COPI[2]};//maybe consider switching to sync_COPI[1];
        end

    end else begin //nCS high so transfer should be complete
       
        if (nCS_rise) begin //if correct number of clock cycles has elapsed.
            
            if (address_decoded && (clk_count == 16)) begin
                data <= packet[7:0];
                address <= packet[11:8];
                transaction_ready <= 1'b1;
            end

        end 

        if (transaction_processed) begin
            transaction_ready <= 1'b0; //clear ready flag
        end
    end
end


always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin //reset device

        transaction_processed <= 1'b0;

        en_reg_out_7_0 <= 8'h00;
        en_reg_out_15_8 <= 8'h00;
        en_reg_pwm_7_0 <= 8'h00;
        en_reg_pwm_15_8 <= 8'h00;
        pwm_duty_cycle <= 8'h00;

    end else if (transaction_ready && !transaction_processed) begin //process SPI packet
        
        case(address)
            4'd0: en_reg_out_7_0 <= data;
            4'd1: en_reg_out_15_8 <= data;
            4'd2: en_reg_pwm_7_0 <= data;
            4'd3: en_reg_pwm_15_8 <= data;
            4'd4: pwm_duty_cycle <= data;
            default: ;
        endcase

        transaction_processed <= 1'b1;

    end else if (!transaction_ready && transaction_processed) begin 
        
        transaction_processed <= 1'b0; // clear processed flag when read is cleared

    end
end

endmodule