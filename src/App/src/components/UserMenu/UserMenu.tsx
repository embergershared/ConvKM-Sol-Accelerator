import React, { useCallback } from "react";
import {
  Avatar,
  Menu,
  MenuItem,
  MenuList,
  MenuPopover,
  MenuTrigger,
  MenuDivider,
  MenuGroupHeader,
} from "@fluentui/react-components";
import { SignOutRegular } from "@fluentui/react-icons";
import "./UserMenu.css";

interface UserMenuProps {
  userName: string;
}

const UserMenu: React.FC<UserMenuProps> = ({ userName }) => {
  const handleSignOut = useCallback(() => {
    localStorage.removeItem("userId");
    window.location.href = "/.auth/logout?post_logout_redirect_uri=/";
  }, []);

  return (
    <Menu>
      <MenuTrigger disableButtonEnhancement>
        <button
          className="user-menu-trigger"
          aria-label={`User menu for ${userName || "user"}`}
          title={userName}
        >
          <Avatar name={userName} />
        </button>
      </MenuTrigger>
      <MenuPopover>
        <MenuList>
          <MenuGroupHeader>{userName || "User"}</MenuGroupHeader>
          <MenuDivider />
          <MenuItem icon={<SignOutRegular />} onClick={handleSignOut}>
            Sign out
          </MenuItem>
        </MenuList>
      </MenuPopover>
    </Menu>
  );
};

export default UserMenu;
