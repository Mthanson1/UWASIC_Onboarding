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

wire sync_COPI, sync_SCLK, sync_nCS, nCS_rise, nCS_fall;
wire [3:0] _unused;
reg [7:0] packet;

sync_chain stable_COPI( //synch chain to stabilize COPI input
    .clk(clk), 
    .async_in(COPI), 
    .sync_out(sync_COPI),
    .rst_n(rst_n),
    .edge_rise(_unused[0]),
    .edge_fall(_unused[1])
);

sync_chain stable_SCLK( //synch chain to stabilize SCLK input 
    .clk(clk),
    .async_in(SCLK),
    .sync_out(_unused[2]),
    .rst_n(rst_n),
    .edge_rise(sync_SCLK),
    .edge_fall(_unused[3])
);

sync_chain stable_nCS( //synch chain to stabilize nCS input
    .clk(clk),
    .async_in(nCS),
    .sync_out(sync_nCS),
    .rst_n(rst_n),
    .edge_rise(nCS_rise),
    .edge_fall(nCS_fall)
);

always @(posedge clk or negedge rst_n) begin
    if(~rst_n) packet <= 0;
    else if (~sync_nCS && sync_SCLK) packet <= {packet[6:0], sync_COPI};
end

reg transaction_ready, transaction_processed;
reg [3:0] clk_count;
reg [1:0] transaction_count;
wire address_decoded = packet[7] & ~|packet[6:4] & (packet[3:0] < 5);
reg [3:0] address;
reg [7:0] data;

//process SPI protocol in clk domain 
always @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin //reset peripheral

        clk_count <= 1'b0;
        transaction_count <= 1'b0;
        transaction_ready <= 1'b0;

    end else if (sync_nCS == 1'b0) begin //nCS is low so start counting clock cycles.
        
        if(nCS_fall) begin 
            clk_count <= 0;
            transaction_count <= 0;
        end
        if(sync_SCLK) clk_count <= clk_count + 1;

    end else begin //nCS high so transfer should be complete
       
        if (nCS_rise && (clk_count == 8)) begin //if correct number of clock cycles has elapsed.
            
            case(transaction_count == 1) 
                2'd0: begin // if address has already been read
                    if (address_decoded) begin
                        address <= packet[3:0];
                        transaction_count <= 2'd1;
                    end
                end
                2'd1: begin
                    data <= packet;
                    transaction_count <= 2'd2;
                    transaction_ready <= 1'b1;
                end
                default: transaction_ready <= 1'd0;
            endcase

        end 

        if (transaction_processed) begin
            transaction_ready <= 1'b0; //clear ready flag
        end
    end
end


always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin //reset device

        transaction_processed <= 1'b0;

    end else if (transaction_ready && !transaction_processed) begin //process SPI packet
        
        case(address)
            4'd0: en_reg_out_7_0 <= data; 
            4'd1: en_reg_out_15_8 <= data;
            4'd2: en_reg_pwm_7_0 <= data;
            4'd3: en_reg_pwm_15_8 <= data;
            4'd4: pwm_duty_cycle <= data;
            default: ;
        endcase

        transaction_count <= 2'b0;
        transaction_processed <= 1'b1;

    end else if (!transaction_ready && transaction_processed) begin 
        
        transaction_processed <= 1'b0; // clear processed flag when read is cleared

    end
end

endmodule

module sync_chain #(
    parameter STAGES = 3 //MUST BE >= 3
) (
    input wire clk,
    input wire async_in,
    input wire rst_n,
    output wire sync_out,
    output wire edge_rise,
    output wire edge_fall
);

reg [STAGES-1:0] sync_ff;

integer i;

always @(posedge clk or negedge rst_n) begin
    if (~rst_n) sync_ff <= {STAGES{1'b0}};
    else begin
        sync_ff[0] <= async_in;
        for (i = 1; i < STAGES; i = i + 1) begin
            sync_ff[i] <= sync_ff[i-1];
        end 
    end
end 

assign sync_out = sync_ff[STAGES-1];
assign edge_rise = sync_ff[STAGES-1] & ~sync_ff[STAGES-2];
assign edge_fall = ~sync_ff[STAGES-1] & sync_ff[STAGES-2];

endmodule