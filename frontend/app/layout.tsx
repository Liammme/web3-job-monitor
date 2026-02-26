import "./globals.css";

export const metadata = {
  title: "Web3 Job Monitor",
  description: "Personal dashboard for web3 jobs monitoring",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
