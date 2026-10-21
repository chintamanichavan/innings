import { redirect } from "next/navigation";

import { HOME_SPORT, link } from "@/lib/sport";

export default function Root() {
  redirect(link(HOME_SPORT));
}
