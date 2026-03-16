export const INDIAN_STATES = [
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
  "Andaman and Nicobar Islands",
  "Chandigarh",
  "Dadra and Nagar Haveli and Daman and Diu",
  "Delhi",
  "Jammu and Kashmir",
  "Ladakh",
  "Lakshadweep",
  "Puducherry",
];

export const GST_RATES = [0, 5, 12, 18, 28];

export function calcGstBreakdown(
  taxableAmount: number,
  gstPercent: number,
  sellerState: string,
  buyerState: string
) {
  if (!gstPercent || gstPercent <= 0) {
    return { taxable: taxableAmount, cgst: 0, sgst: 0, igst: 0, totalTax: 0, total: taxableAmount };
  }
  const gstAmount = Math.round(taxableAmount * gstPercent / 100 * 100) / 100;
  const sameState =
    sellerState && buyerState &&
    sellerState.trim().toLowerCase() === buyerState.trim().toLowerCase();

  if (sameState) {
    const half = Math.round(gstAmount / 2 * 100) / 100;
    return { taxable: taxableAmount, cgst: half, sgst: half, igst: 0, totalTax: Math.round(half * 2 * 100) / 100, total: Math.round((taxableAmount + half * 2) * 100) / 100 };
  } else {
    return { taxable: taxableAmount, cgst: 0, sgst: 0, igst: gstAmount, totalTax: gstAmount, total: Math.round((taxableAmount + gstAmount) * 100) / 100 };
  }
}
