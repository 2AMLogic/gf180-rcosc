v {xschem version=3.4.7 file_version=1.2
* rcosc smoke test (issue #6) -- functional/DC sanity check ONLY.
* Drives trim code 0x80 (mid-scale) and VDD=3.3V; NOT a PVT-corner or
* accuracy claim -- see design/README.md.
}
G {}
K {}
V {}
S {}
E {}
C {rcosc_top.sym} 0 0 0 0 {name=XDUT}
N -62 220.0 -82 220.0 {}
C {lab_pin.sym} -82 220.0 0 0 {name=l1 lab=vdd}
N -62 176.0 -82 176.0 {}
C {lab_pin.sym} -82 176.0 0 0 {name=l2 lab=0}
N -62 132.0 -82 132.0 {}
C {lab_pin.sym} -82 132.0 0 0 {name=l3 lab=clk}
N -62 88.0 -82 88.0 {}
C {lab_pin.sym} -82 88.0 0 0 {name=l4 lab=t0}
N -62 44.0 -82 44.0 {}
C {lab_pin.sym} -82 44.0 0 0 {name=l5 lab=t1}
N -62 0.0 -82 0.0 {}
C {lab_pin.sym} -82 0.0 0 0 {name=l6 lab=t2}
N -62 -44.0 -82 -44.0 {}
C {lab_pin.sym} -82 -44.0 0 0 {name=l7 lab=t3}
N -62 -88.0 -82 -88.0 {}
C {lab_pin.sym} -82 -88.0 0 0 {name=l8 lab=t4}
N -62 -132.0 -82 -132.0 {}
C {lab_pin.sym} -82 -132.0 0 0 {name=l9 lab=t5}
N -62 -176.0 -82 -176.0 {}
C {lab_pin.sym} -82 -176.0 0 0 {name=l10 lab=t6}
N -62 -220.0 -82 -220.0 {}
C {lab_pin.sym} -82 -220.0 0 0 {name=l11 lab=t7}
C {vsource.sym} -400 0 0 0 {name=VDD value="dc 3.3"}
N -400 -30 -400 -50 {}
C {lab_pin.sym} -400 -50 0 0 {name=l12 lab=vdd}
N -400 30 -400 50 {}
C {lab_pin.sym} -400 50 0 0 {name=l13 lab=0}
C {vsource.sym} -400 -300 0 0 {name=VT0 value="dc 0.0"}
N -400 -330 -400 -350 {}
C {lab_pin.sym} -400 -350 0 0 {name=l14 lab=t0}
N -400 -270 -400 -250 {}
C {lab_pin.sym} -400 -250 0 0 {name=l15 lab=0}
C {vsource.sym} -400 -500 0 0 {name=VT1 value="dc 0.0"}
N -400 -530 -400 -550 {}
C {lab_pin.sym} -400 -550 0 0 {name=l16 lab=t1}
N -400 -470 -400 -450 {}
C {lab_pin.sym} -400 -450 0 0 {name=l17 lab=0}
C {vsource.sym} -400 -700 0 0 {name=VT2 value="dc 0.0"}
N -400 -730 -400 -750 {}
C {lab_pin.sym} -400 -750 0 0 {name=l18 lab=t2}
N -400 -670 -400 -650 {}
C {lab_pin.sym} -400 -650 0 0 {name=l19 lab=0}
C {vsource.sym} -400 -900 0 0 {name=VT3 value="dc 0.0"}
N -400 -930 -400 -950 {}
C {lab_pin.sym} -400 -950 0 0 {name=l20 lab=t3}
N -400 -870 -400 -850 {}
C {lab_pin.sym} -400 -850 0 0 {name=l21 lab=0}
C {vsource.sym} -400 -1100 0 0 {name=VT4 value="dc 0.0"}
N -400 -1130 -400 -1150 {}
C {lab_pin.sym} -400 -1150 0 0 {name=l22 lab=t4}
N -400 -1070 -400 -1050 {}
C {lab_pin.sym} -400 -1050 0 0 {name=l23 lab=0}
C {vsource.sym} -400 -1300 0 0 {name=VT5 value="dc 0.0"}
N -400 -1330 -400 -1350 {}
C {lab_pin.sym} -400 -1350 0 0 {name=l24 lab=t5}
N -400 -1270 -400 -1250 {}
C {lab_pin.sym} -400 -1250 0 0 {name=l25 lab=0}
C {vsource.sym} -400 -1500 0 0 {name=VT6 value="dc 0.0"}
N -400 -1530 -400 -1550 {}
C {lab_pin.sym} -400 -1550 0 0 {name=l26 lab=t6}
N -400 -1470 -400 -1450 {}
C {lab_pin.sym} -400 -1450 0 0 {name=l27 lab=0}
C {vsource.sym} -400 -1700 0 0 {name=VT7 value="dc 3.3"}
N -400 -1730 -400 -1750 {}
C {lab_pin.sym} -400 -1750 0 0 {name=l28 lab=t7}
N -400 -1670 -400 -1650 {}
C {lab_pin.sym} -400 -1650 0 0 {name=l29 lab=0}
C {code_shown.sym} 800 0 0 0 {name=s1 only_toplevel=false value="
* pdk_include.spice is generated at run time by regen-netlist.sh /
* run-smoke-test.sh from $PDK_ROOT / $PDK, kept out of this schematic
* so it has no hardcoded, machine-specific path.
.include pdk_include.spice

.control
op
print v(vdd) v(vc) v(vh) v(vl) v(ibias) v(clk)
tran 200p 4000n
meas tran t_first_rise when v(clk)=1.65 rise=1
meas tran t_second_rise when v(clk)=1.65 rise=2
print t_first_rise t_second_rise
quit
.endc
"}
