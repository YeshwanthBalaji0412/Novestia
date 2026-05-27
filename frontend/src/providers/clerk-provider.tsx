"use client";

import { ClerkProvider as BaseClerkProvider } from "@clerk/nextjs";
import { dark } from "@clerk/themes";

export function ClerkProvider({ children }: { children: React.ReactNode }) {
  return (
    <BaseClerkProvider
      appearance={{
        baseTheme: dark,
        variables: {
          colorPrimary: "#5B8DEF",
          colorBackground: "#0F1117",
          colorInputBackground: "#1A1D27",
          colorInputText: "#E8E8ED",
          colorText: "#E8E8ED",
          colorTextSecondary: "#6B7084",
          colorDanger: "#E5534B",
          colorSuccess: "#3FB950",
          colorWarning: "#D29922",
          colorNeutral: "#E8E8ED",
          borderRadius: "0.75rem",
          fontSize: "14px",
        },
        elements: {
          card: {
            backgroundColor: "#0F1117",
            border: "1px solid rgba(255,255,255,0.08)",
            boxShadow: "0 0 40px rgba(91,141,239,0.08)",
          },
          rootBox: {
            width: "100%",
            maxWidth: "420px",
          },
          headerTitle: {
            color: "#E8E8ED",
            fontWeight: "700",
            fontSize: "20px",
          },
          headerSubtitle: {
            color: "#6B7084",
          },
          formFieldLabel: {
            color: "#9CA0B0",
            fontSize: "12px",
            fontWeight: "500",
            textTransform: "uppercase" as const,
            letterSpacing: "0.05em",
          },
          formFieldInput: {
            backgroundColor: "#1A1D27",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#E8E8ED",
            fontSize: "14px",
          },
          formFieldInput__focused: {
            borderColor: "#5B8DEF",
            boxShadow: "0 0 0 1px #5B8DEF",
          },
          formButtonPrimary: {
            backgroundColor: "#5B8DEF",
            color: "#FFFFFF",
            fontWeight: "600",
            fontSize: "14px",
            boxShadow: "0 0 20px rgba(91,141,239,0.2)",
          },
          formButtonPrimary__hover: {
            backgroundColor: "#6E9CF2",
          },
          footerActionLink: {
            color: "#5B8DEF",
          },
          socialButtonsBlockButton: {
            backgroundColor: "transparent",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#E8E8ED",
          },
          socialButtonsBlockButton__hover: {
            backgroundColor: "rgba(255,255,255,0.04)",
            borderColor: "rgba(255,255,255,0.15)",
          },
          dividerLine: {
            backgroundColor: "rgba(255,255,255,0.08)",
          },
          dividerText: {
            color: "#6B7084",
          },
          identityPreview: {
            backgroundColor: "#1A1D27",
            border: "1px solid rgba(255,255,255,0.08)",
          },
          identityPreviewText: {
            color: "#E8E8ED",
          },
          identityPreviewEditButton: {
            color: "#5B8DEF",
          },
          formResendCodeLink: {
            color: "#5B8DEF",
          },
          otpCodeFieldInput: {
            backgroundColor: "#1A1D27",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#E8E8ED",
          },
          alert: {
            backgroundColor: "#1A1D27",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#E8E8ED",
          },
          alertText: {
            color: "#E8E8ED",
          },
          userButtonPopoverCard: {
            backgroundColor: "#0F1117",
            border: "1px solid rgba(255,255,255,0.08)",
          },
          userButtonPopoverActionButton: {
            color: "#E8E8ED",
          },
          userButtonPopoverActionButton__hover: {
            backgroundColor: "rgba(255,255,255,0.04)",
          },
          userButtonPopoverFooter: {
            display: "none",
          },
        },
      }}
    >
      {children}
    </BaseClerkProvider>
  );
}
