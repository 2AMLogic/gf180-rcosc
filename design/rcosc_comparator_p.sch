v {xschem version=3.4.7 file_version=1.2
* rcosc_comparator_p -- complementary (PMOS-input) 5T differential-pair
* open-loop comparator + output buffer, issue #57 (DR-0017). Same cell
* contract as rcosc_comparator.sch (out rises with inp-inn; single-ended
* output on the inp side; diode-connected mirror load on the inn side; one
* CMOS inverter buffer) with every device polarity swapped, so its input
* pair works at the LOW common mode where the NMOS-input cell starves.
*
* Why this cell exists (issue #57, flattening the supply slope DR-0016
* measured at XCMPL): the NMOS-input XCMPL compares vl (= VDD/3) against
* vc as vc falls through it toward ~0 V, so its input pair operates with
* its source (tail) node squeezed against vss -- MTAIL leaves saturation
* exactly at low supply / high-VT corners, the tail current and gm droop,
* and t_cmp_l runs 3.81 ns at ss/27C/3.0 V vs 1.90 ns at 3.6 V (87% of
* that corner's delay-span, DR-0016 F4). Swapping the pair to PMOS
* re-references the same comparison to the vdd rail: at the crossing the
* pair's |VSG| is set by the (supply-independent) tail current, the tail
* device keeps |VDS| headroom at every supply, and as vc dives below vl
* the moving input only INCREASES its overdrive -- the near-ground common
* mode becomes the pair's favorable region instead of its worst one.
* XCMPH (common mode 2/3 VDD) keeps the unchanged NMOS-input cell: it is
* already supply-flat (2.55 -> 2.45 ns, DR-0016 F4) and is not touched.
*
* Bias: MPTAIL mirrors rcosc_bias.sch's P1 (diode-connected pfet, gate
* node pb) at 4:1 -- W=16u nf=4 is four copies of P1's own W=4u unit
* geometry, half the 8:1 ratio MTAIL uses against N1 via the ibias gate
* node. P1:P2 are matched 1:1 so the pb reference carries exactly ibias;
* the XCMPL tail therefore runs at 4x ibias while XCMPH keeps 8x, a
* deliberate re-budget of the DR-0008/DR-0009 budget (17x -> 13x ibias)
* that is PART of this lever, not a side effect: the complementary cell
* at 8x measured 4-6x FASTER than the NMOS cell it replaces (t_cmp_l
* 0.3-0.9 ns), which would cut dsum and raise f at fixed trim code --
* colliding with DR-0003 Row 4's knife-edge Iq margin exactly the way
* DR-0016's lever-(a) rejection warned. Halving the tail lands the stage
* at its nominal-delay target (measured sizing pass: t_cmp_l ~= 1.6-2.1
* ns flat, vs the NMOS cell's 1.3...5.0 ns supply/corner spread) AND
* widens Row 4's margin (Iq drops ~4x ibias at every cell; the guardrail
* cell 0x80/ff/85C/3.6V drops from 58.22 to 55.36 MHz). pb is exported
* from rcosc_bias for this purpose (new pin, issue #57); it was always
* an internal node of the beta-multiplier.
*
* Input mapping and delay shaping (measured, issue #57 sizing pass): the
* moving input (XCMPL's inn = vc, the diving node) drives the OUTPUT-side
* pfet MPINP, and the fixed threshold (inp = vl) drives the diode-side
* pfet MPINN, so the output pole is charged against the quasi-static
* mirror rather than slewed directly by the moving input. With the moving
* input on the output side the single-ended output on dp becomes NEGATED
* w.r.t. the (inp - inn) contract, so the buffer is a two-inverter chain
* (MBUF1 + MBUF2) restoring out to (inp - inn) and keeping the
* latch-facing polarity identical to rcosc_comparator. The first
* inverter's pull-down is deliberately weak (MBUFN W=0.5u vs MBUFP 4u,
* both L=0.5u): its trip sits high, so dp must charge most of its swing
* before cmpl_out moves -- this is the stage's dominant delay knob and
* it is ratiometric (a geometry ratio, not a current), so it adds delay
* without adding supply slope.
*
* Device sizing (measured sizing pass, issue #57): pair W=8u L=0.5u nf=4,
* tail W=16u L=1u nf=4, NMOS mirror loads W=4u L=1u matching the pfet
* loads of the NMOS cell, MBUFP 4u / MBUFN 0.5u (L=0.5u) first inverter,
* MBUF2P 4u / MBUF2N 2u (L=0.5u) second inverter. The full PVT factorial
* re-run and the DR-0016 probe decomposition are the evidence, per repo
* convention.
}
G {}
K {}
V {}
S {}
E {}
C {symbols/pfet_03v3.sym} 0 0 0 0 {name=MPTAIL model=pfet_03v3 W=16u L=1u nf=4 m=1}
N 20 -30 20 -50 {}
C {lab_pin.sym} 20 -50 0 0 {name=l1 lab=vdd}
N -20 0 -40 0 {}
C {lab_pin.sym} -40 0 0 0 {name=l2 lab=pb}
N 20 30 20 50 {}
C {lab_pin.sym} 20 50 0 0 {name=l3 lab=tailp}
N 20 0 40 0 {}
C {lab_pin.sym} 40 0 0 0 {name=l4 lab=vdd}
C {symbols/pfet_03v3.sym} 200 0 0 0 {name=MPINP model=pfet_03v3 W=8u L=0.5u nf=4 m=1}
N 220 -30 220 -50 {}
C {lab_pin.sym} 220 -50 0 0 {name=l5 lab=tailp}
N 180 0 160 0 {}
C {lab_pin.sym} 160 0 0 0 {name=l6 lab=inn}
N 220 30 220 50 {}
C {lab_pin.sym} 220 50 0 0 {name=l7 lab=dp}
N 220 0 240 0 {}
C {lab_pin.sym} 240 0 0 0 {name=l8 lab=vdd}
C {symbols/pfet_03v3.sym} 400 0 0 0 {name=MPINN model=pfet_03v3 W=8u L=0.5u nf=4 m=1}
N 420 -30 420 -50 {}
C {lab_pin.sym} 420 -50 0 0 {name=l9 lab=tailp}
N 380 0 360 0 {}
C {lab_pin.sym} 360 0 0 0 {name=l10 lab=inp}
N 420 30 420 50 {}
C {lab_pin.sym} 420 50 0 0 {name=l11 lab=dn}
N 420 0 440 0 {}
C {lab_pin.sym} 440 0 0 0 {name=l12 lab=vdd}
C {symbols/nfet_03v3.sym} 600 0 0 0 {name=MNLOADA model=nfet_03v3 W=4u L=1u nf=1 m=1}
N 620 -30 620 -50 {}
C {lab_pin.sym} 620 -50 0 0 {name=l13 lab=dn}
N 580 0 560 0 {}
C {lab_pin.sym} 560 0 0 0 {name=l14 lab=dn}
N 620 30 620 50 {}
C {lab_pin.sym} 620 50 0 0 {name=l15 lab=vss}
N 620 0 640 0 {}
C {lab_pin.sym} 640 0 0 0 {name=l16 lab=vss}
C {symbols/nfet_03v3.sym} 800 0 0 0 {name=MNLOADB model=nfet_03v3 W=4u L=1u nf=1 m=1}
N 820 -30 820 -50 {}
C {lab_pin.sym} 820 -50 0 0 {name=l17 lab=dp}
N 780 0 760 0 {}
C {lab_pin.sym} 760 0 0 0 {name=l18 lab=dn}
N 820 30 820 50 {}
C {lab_pin.sym} 820 50 0 0 {name=l19 lab=vss}
N 820 0 840 0 {}
C {lab_pin.sym} 840 0 0 0 {name=l20 lab=vss}
C {symbols/pfet_03v3.sym} 1000 0 0 0 {name=MBUFP model=pfet_03v3 W=4u L=0.5u nf=1 m=1}
N 1020 -30 1020 -50 {}
C {lab_pin.sym} 1020 -50 0 0 {name=l21 lab=vdd}
N 980 0 960 0 {}
C {lab_pin.sym} 960 0 0 0 {name=l22 lab=dp}
N 1020 30 1020 50 {}
C {lab_pin.sym} 1020 50 0 0 {name=l23 lab=outb}
N 1020 0 1040 0 {}
C {lab_pin.sym} 1040 0 0 0 {name=l24 lab=vdd}
C {symbols/nfet_03v3.sym} 1200 0 0 0 {name=MBUFN model=nfet_03v3 W=0.5u L=0.5u nf=1 m=1}
N 1220 -30 1220 -50 {}
C {lab_pin.sym} 1220 -50 0 0 {name=l25 lab=outb}
N 1180 0 1160 0 {}
C {lab_pin.sym} 1160 0 0 0 {name=l26 lab=dp}
N 1220 30 1220 50 {}
C {lab_pin.sym} 1220 50 0 0 {name=l27 lab=vss}
N 1220 0 1240 0 {}
C {lab_pin.sym} 1240 0 0 0 {name=l28 lab=vss}
C {symbols/pfet_03v3.sym} 1400 0 0 0 {name=MBUF2P model=pfet_03v3 W=4u L=0.5u nf=1 m=1}
N 1420 -30 1420 -50 {}
C {lab_pin.sym} 1420 -50 0 0 {name=l29 lab=vdd}
N 1380 0 1360 0 {}
C {lab_pin.sym} 1360 0 0 0 {name=l30 lab=outb}
N 1420 30 1420 50 {}
C {lab_pin.sym} 1420 50 0 0 {name=l31 lab=out}
N 1420 0 1440 0 {}
C {lab_pin.sym} 1440 0 0 0 {name=l32 lab=vdd}
C {symbols/nfet_03v3.sym} 1600 0 0 0 {name=MBUF2N model=nfet_03v3 W=2u L=0.5u nf=1 m=1}
N 1620 -30 1620 -50 {}
C {lab_pin.sym} 1620 -50 0 0 {name=l33 lab=out}
N 1580 0 1560 0 {}
C {lab_pin.sym} 1560 0 0 0 {name=l34 lab=outb}
N 1620 30 1620 50 {}
C {lab_pin.sym} 1620 50 0 0 {name=l35 lab=vss}
N 1620 0 1640 0 {}
C {lab_pin.sym} 1640 0 0 0 {name=l36 lab=vss}
C {iopin.sym} -200 300 0 0 {name=p29 lab=vdd}
C {iopin.sym} -200 240 0 0 {name=p30 lab=vss}
C {iopin.sym} -200 180 0 0 {name=p31 lab=pb}
C {iopin.sym} -200 120 0 0 {name=p32 lab=inp}
C {iopin.sym} -200 60 0 0 {name=p33 lab=inn}
C {iopin.sym} -200 0 0 0 {name=p34 lab=out}
