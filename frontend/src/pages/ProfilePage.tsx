import { AccountSection } from "../components/AccountSection";
import { useNavHotkeys } from "../hooks/useNavHotkeys";
import "./settings.css";

export function ProfilePage() {
  useNavHotkeys();
  return (
    <div className="tf-settings">
      <AccountSection />
    </div>
  );
}
