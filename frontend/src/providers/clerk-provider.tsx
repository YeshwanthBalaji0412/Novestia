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
          colorInputText: "#f5f5f7",
          colorText: "#f5f5f7",
          colorTextSecondary: "#c2c2cc",
          colorTextOnPrimaryBackground: "#ffffff",
          colorDanger: "#E5534B",
          colorSuccess: "#3FB950",
          colorWarning: "#D29922",
          colorNeutral: "#c2c2cc",
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
            color: "#f5f5f7",
            fontWeight: "700",
            fontSize: "20px",
          },
          headerSubtitle: {
            color: "#c2c2cc",
          },
          formFieldLabel: {
            color: "#c2c2cc",
            fontSize: "12px",
            fontWeight: "500",
            textTransform: "uppercase" as const,
            letterSpacing: "0.05em",
          },
          formFieldInput: {
            backgroundColor: "#1A1D27",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#f5f5f7",
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
          footerActionText: {
            color: "#c2c2cc",
          },
          footerActionLink: {
            color: "#5B8DEF",
            fontWeight: "500",
          },
          footer: {
            "& *": {
              color: "#8e8e9a !important",
            },
          } as Record<string, unknown>,
          socialButtonsBlockButton: {
            backgroundColor: "transparent",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#f5f5f7",
          },
          socialButtonsBlockButton__hover: {
            backgroundColor: "rgba(255,255,255,0.04)",
            borderColor: "rgba(255,255,255,0.15)",
          },
          dividerLine: {
            backgroundColor: "rgba(255,255,255,0.08)",
          },
          dividerText: {
            color: "#8e8e9a",
          },
          identityPreview: {
            backgroundColor: "#1A1D27",
            border: "1px solid rgba(255,255,255,0.08)",
          },
          identityPreviewText: {
            color: "#f5f5f7",
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
            color: "#f5f5f7",
          },
          alert: {
            backgroundColor: "#1A1D27",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#f5f5f7",
          },
          alertText: {
            color: "#f5f5f7",
          },
          userButtonPopoverCard: {
            backgroundColor: "#0F1117",
            border: "1px solid rgba(255,255,255,0.08)",
          },
          userButtonPopoverActionButton: {
            color: "#f5f5f7",
          },
          userButtonPopoverActionButtonText: {
            color: "#f5f5f7",
          },
          userButtonPopoverActionButtonIcon: {
            color: "#c2c2cc",
          },
          userButtonPopoverActionButton__hover: {
            backgroundColor: "rgba(255,255,255,0.04)",
          },
          userPreviewMainIdentifier: {
            color: "#f5f5f7",
          },
          userPreviewSecondaryIdentifier: {
            color: "#c2c2cc",
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
