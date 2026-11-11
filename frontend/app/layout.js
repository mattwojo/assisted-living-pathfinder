import "./style.css";

export const metadata = {
  title: "Assisted Living Pathfinder",
  description: "Explore and understand assisted living communities.",
};

export default function RootLayout({ children }) {
  return <html lang="en"><body>{children}</body></html>;
}
