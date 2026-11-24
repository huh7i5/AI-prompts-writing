# Did the library’s evening attendance rate change?

[简体中文](reading-room.md) · [Back to the prompt library](../../README.en.md#records)

Copy the whole block into your AI chat. The figures are made up for practice. Try the calculation yourself before you compare answers.

```text
I’m writing the library’s monthly report. Use the booking records below to calculate attendance rates for March and April. Give me the rate for each evening slot and for each month overall. Show the numerator and denominator for each rate.

Then write up to three sentences for the report. Express changes in percentage points. If the results by slot and by month move in different directions, use the figures to explain why. Use only the information provided about the bookings.

My material
These are fictional reading-room records. Each booking covers one seat in one time slot. A check-in counts as attendance for that booking.
Month,Time slot,Bookings,Check-ins
March,6–8 pm,80,72
March,8–10 pm,20,10
April,6–8 pm,20,19
April,8–10 pm,80,44
```

<details>
<summary><strong>See the worked answer and calculations</strong></summary>

| Time slot | March attendance | April attendance | Change |
| --- | ---: | ---: | ---: |
| 6–8 pm | 72 / 80 = 90% | 19 / 20 = 95% | +5 percentage points |
| 8–10 pm | 10 / 20 = 50% | 44 / 80 = 55% | +5 percentage points |
| Both slots | (72 + 10) / (80 + 20) = 82% | (19 + 44) / (20 + 80) = 63% | −19 percentage points |

**Report paragraph**

Overall attendance for evening bookings fell from 82% in March to 63% in April, a drop of 19 percentage points. Attendance rose by 5 percentage points within each time slot. The 8–10 pm slot had the lower attendance rate in both months, and its share of all bookings grew from 20% to 80%, giving it more weight in April’s overall rate.

You can check April’s total by counting bookings. There were 63 check-ins for 100 bookings, giving 63%. Averaging the two slot rates gives 75%, which gives the slot with 20 bookings the same weight as the one with 80.

</details>

[Read the sample paper built from these four booking records](reading-room-paper.en.md)
