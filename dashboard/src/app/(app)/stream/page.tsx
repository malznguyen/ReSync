import { redirect } from "next/navigation";

export default function StreamRedirectPage(): never {
  redirect("/streams");
}
