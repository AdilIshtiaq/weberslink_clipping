import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages, getTranslations } from "next-intl/server";
import { Archivo, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/theme-provider";
import { intlLocale } from "@/i18n/config";
import { COMPANY_NAME, getSiteUrl } from "@/lib/site";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
});

// Display face used on weberslink.org: Archivo, with its width axis for the wide headline look.
const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  axes: ["wdth"],
});


export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("metadata");

  return {
  title: {
    default: t("title"),
    template: t("titleTemplate"),
  },
  description: t("description"),
  metadataBase: new URL(getSiteUrl()),
  applicationName: "WeberslinkClip",
  authors: [{ name: "WeberslinkClip Team", url: getSiteUrl() }],
  creator: "WeberslinkClip Team",
  publisher: COMPANY_NAME,
  category: t("category"),
  icons: {
    icon: "/icon.png",
  },
  openGraph: {
    title: t("title"),
    description: t("openGraphDescription"),
    siteName: "WeberslinkClip",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: t("title"),
    description: t("twitterDescription"),
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
  };
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={intlLocale(locale)} suppressHydrationWarning>
      <head>
      </head>
      <body className={`${inter.variable} ${jetbrainsMono.variable} ${archivo.variable} antialiased`}>
        <ThemeProvider>
          <NextIntlClientProvider locale={locale} messages={messages}>
            <TooltipProvider>
              {children}
              <Toaster />
            </TooltipProvider>
          </NextIntlClientProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
