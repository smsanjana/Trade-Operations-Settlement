import "./globals.css";

export const metadata = {
  title: "Trade Operations Console",
  description: "Evidence-first settlement exception review and approval",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
