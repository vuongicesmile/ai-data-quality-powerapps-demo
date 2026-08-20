import { createLightTheme, type BrandVariants, type Theme } from "@fluentui/react-components";

const dataQualityBrand: BrandVariants = {
  10: "#020305", 20: "#101C29", 30: "#102D44", 40: "#0E3E60", 50: "#0B4F7D",
  60: "#06619A", 70: "#0072B8", 80: "#0078D4", 90: "#2889DA", 100: "#489AE0",
  110: "#64ABE5", 120: "#7EBBEA", 130: "#97CCEF", 140: "#AFDCF4", 150: "#C7ECF8", 160: "#E0FBFC",
};

export const dataQualityTheme: Theme = {
  ...createLightTheme(dataQualityBrand),
  colorBrandBackground: "#0078D4",
  colorBrandBackgroundHover: "#106EBE",
  colorNeutralBackground1: "#FFFFFF",
  colorNeutralBackground2: "#FAFAFA",
  colorNeutralForeground1: "#201F1E",
  colorNeutralForeground2: "#605E5C",
  colorNeutralStroke1: "#EDEBE9",
  borderRadiusMedium: "4px",
  fontFamilyBase: '"Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif',
};
